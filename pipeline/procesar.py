"""Orquestación: PDF(s) de una sesión/partido → Excel del microciclo → Disponibilidad → app."""
import datetime as dt
import os
import re
import shutil
import subprocess

import openpyxl

from . import acumulado, carga_ac, disponibilidad, estados as E, informe, lesiones as L, microciclo
from . import partido, referencia, sesion
from . import config as C
from .xlsx import backup, filas_jugadores, microciclos_existentes, num, plantilla_de


class NecesitaDecision(Exception):
    """Algo que no se puede deducir de los datos: hay que preguntar al preparador."""


def localizar(key):
    """-> (n, ruta) del microciclo que tiene la hoja `{key}_GPS`."""
    for n, ruta in microciclos_existentes().items():
        wb = openpyxl.load_workbook(ruta, read_only=True)
        nombres = wb.sheetnames
        wb.close()
        if f"{key}_GPS" in nombres:
            return n, ruta
    raise ValueError(f"No encuentro la hoja {key}_GPS en ningún Microciclo *.xlsx "
                     f"(¿falta abrir el microciclo?)")


def localizar_por_fecha(fecha):
    """Microciclo cuya semana (lunes-domingo) contiene la fecha."""
    for n, ruta in microciclos_existentes().items():
        wb = openpyxl.load_workbook(ruta, read_only=True)
        fechas = []
        for ws in wb.worksheets:
            if ws.title.endswith("_GPS"):
                m = re.search(r"(\d{2})/(\d{2})/(\d{4})", str(next(ws.iter_rows(max_row=1, values_only=True))[0]))
                if m:
                    fechas.append(dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
        wb.close()
        if fechas and min(fechas) - dt.timedelta(days=min(fechas).weekday()) <= fecha <= max(fechas):
            return n, ruta
    raise ValueError(f"Ningún microciclo cubre el {fecha:%d/%m/%Y}")


def _ultimo_partido_antes(fecha):
    mejor = None
    for n, ruta in microciclos_existentes().items():
        wb = openpyxl.load_workbook(ruta, data_only=True)
        for x in wb.sheetnames:
            if re.match(r"^(PT|J)\d+_GPS$", x):
                from .xlsx import fecha_hoja
                f = fecha_hoja(wb[x])
                if f and f < fecha and (mejor is None or f > mejor[0]):
                    mejor = (f, wb[x])
    return mejor[1] if mejor else None


# ---------------------------------------------------------------------------- leer
def leer(pdfs, carpeta_png):
    """Resumen para decidir estados antes de procesar."""
    infs = [informe.leer(p) for p in pdfs]
    principal = next((i for i in infs if i.codigo), infs[0])
    key = principal.codigo
    n, ruta = localizar(key) if key else localizar_por_fecha(principal.fecha)
    wb = openpyxl.load_workbook(ruta, data_only=True)
    hoja = wb[f"{key}_GPS"] if key else next(wb[x] for x in wb.sheetnames if C.SHEET_KEY_RE.match(x))
    nombres, grupos = plantilla_de(hoja)
    est = E.cargar()
    lineas = [f"Microciclo {n} · hoja {key or '(Extra, sin código)'} · {principal.titulo} "
              f"[{principal.etiqueta}] · {principal.fecha:%a %d/%m/%Y}"]
    en_pdf = {}
    for inf in infs:
        datos, sin = informe.datos_por_dorsal(inf, nombres)
        if sin:
            lineas.append(f"  ⚠ SIN CRUZAR con la plantilla ({os.path.basename(inf.ruta)}): {sin}")
        for d, v in datos.items():
            en_pdf[d] = (v, os.path.basename(inf.ruta))
    duraciones = {}
    for d, (v, _) in en_pdf.items():
        duraciones.setdefault(v["dur"], []).append(d)
    lineas.append("  Grupos por duración: " + " · ".join(
        f"{mins}' → {len(ds)} ({', '.join(nombres[x] for x in sorted(ds)) if len(ds) <= 4 else '...'})"
        for mins, ds in sorted(duraciones.items(), reverse=True)))
    obj = {}
    if key and not C.is_match_key(key):
        filas, _ = filas_jugadores(hoja)
        obj = {d: sesion.tiene_objetivo(hoja, r) for d, r in filas.items()}
    lineas.append("  Dorsal Jugador          Vigente  Obj  En PDF")
    for d in sorted(nombres):
        v = en_pdf.get(d)
        pdf_txt = f"{v[0]['dur']}' PL {v[0]['pl']}" if v else "—  (NO ESTÁ)"
        lineas.append(f"  {d:>6} {str(nombres[d])[:16]:16} {E.vigente(est, d):8} "
                      f"{'sí' if obj.get(d) else '—':4} {pdf_txt}")
    pngs = []
    for inf in infs:
        pngs += informe.pdf_catapult.render_resumen(inf, carpeta_png)
    lineas.append("  Resumen (donut de participación, bloques): " + ", ".join(pngs))
    return "\n".join(lineas)


# ------------------------------------------------------------------------ procesar
def decidir_estados(roster, en_pdf, vigentes, override, es_partido):
    """Estado del día por dorsal. Lanza NecesitaDecision si hay algo que no se puede inferir."""
    out, dudas = {}, []
    for d in roster:
        if d in override:
            out[d] = override[d]
            continue
        vig = vigentes.get(d, C.FULL)
        if d in en_pdf:
            if vig == C.LESION:
                dudas.append(f"{d}: está LESIONADO pero aparece en el PDF → ¿rehab o full?")
            out[d] = C.FULL if es_partido else vig
        else:
            if vig == C.LESION:
                out[d] = C.LESION
            elif es_partido and vig == C.REHAB:
                out[d] = C.REHAB
            else:
                dudas.append(f"{d}: está '{vig}' y NO aparece en el PDF → "
                             + ("¿nc (convocado, no jugó), noconv, lesion?" if es_partido
                                else "¿descanso, lesion o rehab (en otro informe)?"))
    if dudas:
        raise NecesitaDecision("\n".join(dudas))
    return out


def procesar(pdfs, override=None, fallos_gps=None, nota="", extra=False, dry_run=False,
             alias=None, rol_md1=None, tipos_lesion=None):
    """Devuelve un dict-resumen. dry_run: escribe en el scratchpad, no toca nada real."""
    override = override or {}
    fallos_gps = fallos_gps or {}
    infs = [informe.leer(p) for p in pdfs]
    principal = next((i for i in infs if i.codigo), None)
    if principal is None and not extra:
        raise NecesitaDecision("Ningún PDF trae código de sesión/partido (S##/J#/PT#): si es una "
                               "sesión fuera de calendario usa --extra; si es un rehab del mismo "
                               "día que una sesión, pásalo junto al PDF de esa sesión.")
    fecha = (principal or infs[0]).fecha
    key = principal.codigo if principal else f"Extra_{fecha:%d-%m}"
    n, ruta = localizar(key) if principal else localizar_por_fecha(fecha)
    wb = openpyxl.load_workbook(ruta)
    wt = openpyxl.load_workbook(C.TIPO_XLSX)
    ref, coefs = referencia.ref_partido(wt), referencia.coeficientes(wt)
    est = E.cargar()
    res = {"key": key, "microciclo": n, "fecha": fecha.isoformat(), "avisos": []}

    if extra:
        return _procesar_extra(wb, ruta, n, key, fecha, infs, alias, est, res, dry_run, nota)

    ws = wb[f"{key}_GPS"]
    es_partido = C.is_match_key(key)
    nombres, _ = plantilla_de(ws)
    datos = {}
    for inf in infs:
        dd, sin = informe.datos_por_dorsal(inf, nombres, alias)
        if sin:
            raise NecesitaDecision(f"Nombres del PDF que no cruzan con la plantilla: {sin} "
                                   f"(¿fichaje nuevo? usa --alias 'NOMBRE=dorsal')")
        dup = set(dd) & set(datos)
        if dup:
            raise NecesitaDecision(f"Jugadores en más de un PDF: {sorted(dup)}")
        datos.update(dd)
    for d in fallos_gps:
        override.setdefault(d, C.FULL)
    vigentes = {d: E.vigente(est, d) for d in nombres}
    en_pdf = set(datos) | set(fallos_gps)
    estados_dia = decidir_estados(sorted(nombres), en_pdf, vigentes, override, es_partido)
    les = L.cargar()
    _registro_lesiones(les, estados_dia, nombres, fecha.isoformat(), tipos_lesion or {}, res)

    if es_partido:
        ppm = partido.pl_por_metro(datos)
        duracion = referencia.duracion_partido(v.get("min") or v.get("dur") for v in datos.values())
        res["duracion_partido"] = duracion
        for d, mins in fallos_gps.items():
            if d not in ref:
                raise NecesitaDecision(f"{d}: fallo de GPS pero no tiene REF_PARTIDO para estimar")
            datos[d] = partido.estimar_por_fallo(ref[d], mins, duracion, ppm)
        partido.rellenar(ws, datos)
        partido.marcar_cargado(ws)
        _, media = filas_jugadores(ws)
        partido.escribir_notas(ws, media, _notas_partido(nombres, estados_dia, fallos_gps, nota))
        for d, e in estados_dia.items():
            if e in E.PERSISTENTES and e != vigentes[d] and d not in datos:
                E.cambiar(est, d, e, fecha.isoformat(), f"{key}")
        if partido.cuenta_para_ref(key) and not dry_run:
            reales = {d: v for d, v in datos.items() if d not in fallos_gps}
            nombres_ref = {d: wt["REF_PARTIDO"].cell(r, 2).value
                           for d, r in referencia.filas_ref(wt["REF_PARTIDO"]).items()}
            act, cameos = partido.actualizar_ref(wt, key, fecha.isoformat(), reales, nombres_ref, duracion)
            res["ref_actualizados"] = len(act)
            if cameos:
                res["avisos"].append("Cameos cortos en REF_PARTIDO: " + ", ".join(
                    f"{nombres.get(d, d)} ({m:.0f}')" for d, m in cameos))
    else:
        # cambios de estado → objetivos desde hoy en adelante (no retroactivo)
        tocadas = {}
        for d, e in estados_dia.items():
            antes = vigentes[d]
            cambia = (e in E.PERSISTENTES and e != antes) or e == C.DESCANSO
            if not cambia:
                continue
            rol = None
            if e == C.FULL and sesion.tipo_y_dia(ws)[1] == "MD+1":
                rol = (rol_md1 or {}).get(d)
                if rol is None:
                    ult = _ultimo_partido_antes(fecha)
                    rol = microciclo.roles_md1(ult).get(d, "S") if ult is not None else "S"
            tocadas[d] = sesion.ajustar_objetivos(wb, key, d, e, ref, coefs, rol_md1=rol)
            if e in E.PERSISTENTES:
                E.cambiar(est, d, e, fecha.isoformat(), key)
                res["avisos"].append(f"Cambio de estado: {nombres[d]} {antes} → {e} "
                                     f"(objetivos ajustados en {', '.join(tocadas[d]) or '—'})")
        sesion.rellenar(ws, datos, estados_dia)
        _, media = filas_jugadores(ws)
        sesion.escribir_notas(ws, media, sesion.nota_estados(nombres, estados_dia, nota))

    acumulado.recalcular(wb)
    hist = carga_ac.historial({n: wb})
    asof, acwr = carga_ac.rellenar(wb, n, hist)
    res["acwr_fecha"] = asof.isoformat() if asof else None
    res["acwr_altos"] = sorted(
        (nombres.get(d, d), met, v) for d, mets in acwr.items() for met, v in mets.items()
        if v > 1.5 and estados_dia.get(d) == C.FULL)
    E.registrar_sesion(est, key, fecha.isoformat(), estados_dia)
    res["estados"] = {nombres[d]: e for d, e in estados_dia.items() if e != C.FULL}
    return _guardar(wb, ruta, n, wt if (es_partido and partido.cuenta_para_ref(key)) else None,
                    est, ws, res, dry_run, les)


def _registro_lesiones(les, estados_dia, nombres, fecha, tipos, res):
    """Abre una lesión al pasar a lesión/rehab (hace falta el tipo) y la cierra al volver a full."""
    faltan = [d for d, e in estados_dia.items()
              if e in (C.LESION, C.REHAB) and not L.abierta(les, d) and d not in tipos]
    if faltan:
        raise NecesitaDecision("Lesión nueva sin tipo: " + ", ".join(
            f"{nombres[d]} ({estados_dia[d]})" for d in faltan)
            + " → ¿qué lesión es? (--lesion DORSAL='tipo'; si no es una lesión, usa otro estado)")
    for d, e in estados_dia.items():
        if e in (C.LESION, C.REHAB) and not L.abierta(les, d):
            L.abrir(les, d, tipos[d], fecha)
            res["avisos"].append(f"Lesión abierta: {nombres[d]} · {tipos[d]} · baja {fecha}")
        elif e == C.FULL and L.abierta(les, d):
            l = L.cerrar(les, d, fecha)
            res["avisos"].append(f"Alta: {nombres[d]} · {l['tipo']} ({l['baja']} → {fecha})")


def _notas_partido(nombres, estados_dia, fallos_gps, nota):
    grupos = {}
    for d, e in sorted(estados_dia.items()):
        grupos.setdefault(e, []).append(nombres[d])
    lineas = []
    if grupos.get(C.LESION) or grupos.get(C.REHAB):
        lineas.append("LESIONADOS (pendientes de alta, sin datos): " + " · ".join(grupos.get(C.LESION, []))
                      + (". Rehab (no disputaron el partido): " + " · ".join(grupos[C.REHAB])
                         if grupos.get(C.REHAB) else ""))
    for d, mins in fallos_gps.items():
        lineas.append(f"{nombres[d]}: fallo de dispositivo GPS — datos reconstruidos a partir de su "
                      f"REF_PARTIDO propio escalado a {mins:.0f}' jugados con la fórmula de fatiga (estimado, no es GPS real). "
                      f"Excluido de la actualización de REF_PARTIDO de este partido.")
    if grupos.get(C.NC):
        lineas.append("Convocado, no jugó: " + " · ".join(grupos[C.NC]))
    if grupos.get(C.NOCONV):
        lineas.append("No convocado (decisión técnica): " + " · ".join(grupos[C.NOCONV]))
    if nota:
        lineas.append(nota)
    return lineas


def _procesar_extra(wb, ruta, n, key, fecha, infs, alias, est, res, dry_run, nota):
    """Sesión fuera de calendario: hoja Extra_dd-mm_GPS (no cuenta para media ni Disponibilidad)."""
    base = next(wb[x] for x in wb.sheetnames if C.SHEET_KEY_RE.match(x) and C.is_match_key(x[:-4]))
    nombres, grupos = plantilla_de(base)
    datos = {}
    for inf in infs:
        dd, sin = informe.datos_por_dorsal(inf, nombres, alias)
        if sin:
            raise NecesitaDecision(f"Nombres del PDF que no cruzan con la plantilla: {sin}")
        datos.update(dd)
    nombre = f"{key}_GPS"
    if nombre in wb.sheetnames:
        del wb[nombre]
    ws = wb.create_sheet(nombre, index=wb.sheetnames.index("Acumulado"))
    dia = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][fecha.weekday()]
    quien = ", ".join(nombres[d] for d in sorted(datos))
    ws.cell(1, 1, f"SESIÓN EXTRA · {dia} {fecha:%d/%m/%Y} — fuera de la planificación semanal")
    ws.cell(2, 1, f"Sesión adicional para {quien}. NO cuenta para la media del equipo, NO se compara "
                  "contra objetivo y NO entra en Disponibilidad y Minutos. SÍ se suma al Acumulado "
                  f"individual y al ACWR (PL, HSR y Sprint) de estos jugadores. {nota}".strip())
    for j, h in enumerate(["Dorsal", "Jugador", "Grupo", "Distancia (m)", "HMLD (m)", "HSR (m)",
                           "Sprint (#)", "ACC (#)", "DEC (#)", "Vel Máx\n(km/h)", "Player\nLoad",
                           "Duración"], start=1):
        ws.cell(4, j, h)
    for i, d in enumerate(sorted(datos)):
        v = datos[d]
        fila = [d, nombres[d], grupos[d]] + [v[m] for m in C.METRICS] + [v["vmax"], v["pl"], v["dur"]]
        for j, x in enumerate(fila, start=1):
            ws.cell(5 + i, j, x)
    acumulado.recalcular(wb)
    hist = carga_ac.historial({n: wb})
    asof, _ = carga_ac.rellenar(wb, n, hist)
    res["acwr_fecha"] = asof.isoformat() if asof else None
    res["estados"] = {}
    return _guardar(wb, ruta, n, None, est, ws, res, dry_run)


def _guardar(wb, ruta, n, wt, est, ws, res, dry_run, les=None):
    esperado = {(r[0].row, c.column): c.value for r in ws.iter_rows() for c in r if c.value is not None}
    if dry_run:
        destino = os.path.join(C.GPS_DIR, "_prueba")
        os.makedirs(destino, exist_ok=True)
        ruta = os.path.join(destino, os.path.basename(ruta))
        res["dry_run"] = ruta
    else:
        res["backup"] = backup([ruta, C.TIPO_XLSX, C.DISPO_XLSX, C.ESTADOS_JSON, L.RUTA])
    wb.save(ruta)
    # verificación: releer y comparar la hoja procesada celda a celda
    ws2 = openpyxl.load_workbook(ruta)[ws.title]
    leido = {(r[0].row, c.column): c.value for r in ws2.iter_rows() for c in r if c.value is not None}
    if leido != esperado:
        raise RuntimeError(f"Verificación fallida al releer {ws.title}")
    if not dry_run:
        if wt is not None:
            wt.save(C.TIPO_XLSX)
        E.guardar(est)
        if les is not None:
            L.guardar(les)
        disponibilidad.generar()
    res["guardado"] = ruta
    return res


# ------------------------------------------------------------------------ publicar
def importar(avisar):
    args = ["python3", os.path.join(C.REPO_DIR, "import_data.py")]
    if not avisar:
        args.append("--sin-avisar")
    return subprocess.run(args, cwd=C.REPO_DIR, capture_output=True, text=True, check=True).stdout


def publicar(mensaje):
    def git(*a):
        return subprocess.run(["git", *a], cwd=C.REPO_DIR, capture_output=True, text=True, check=True).stdout
    git("add", "data.js")
    if not subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=C.REPO_DIR).returncode:
        return "sin cambios en data.js"
    git("commit", "-m", mensaje)
    git("push")
    return "publicado"
