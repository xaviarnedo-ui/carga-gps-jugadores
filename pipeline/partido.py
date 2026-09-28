"""Hojas de partido (J#/PT#_GPS) y de sesión Extra, y actualización de REF_PARTIDO."""
import datetime as dt
import json
import os
import re

from . import config as C
from . import referencia
from .xlsx import filas_jugadores, limpio, num, r1, vaciar

CAMEO_MIN = 30


def rellenar(ws, datos):
    """datos: {dorsal: valores}. Sin Obj/Dif/semáforo; quien no jugó queda vacío."""
    filas, fila_media = filas_jugadores(ws)
    fuera = sorted(set(datos) - set(filas))
    if fuera:
        raise ValueError(f"{ws.title}: dorsales del PDF que no están en la hoja: {fuera}")
    for dorsal, fila in filas.items():
        d = datos.get(dorsal)
        for m, c in C.MAT_COL.items():
            cell = ws.cell(fila, c)
            if d is None:
                vaciar(cell)
            else:
                cell.value = d[m]
        for col, k in ((C.MAT_VMAX, "vmax"), (C.MAT_PL, "pl"), (C.MAT_DUR, "dur")):
            cell = ws.cell(fila, col)
            if d is None or d.get(k) is None:
                vaciar(cell)
            else:
                cell.value = d[k]
    if fila_media:
        con_dato = [filas[d] for d in datos if d in filas]

        def media(col, dec):
            vals = [num(ws.cell(r, col).value) for r in con_dato]
            vals = [v for v in vals if v is not None]
            return round(sum(vals) / len(vals), dec) if vals else None
        for m, c in C.MAT_COL.items():
            ws.cell(fila_media, c).value = limpio(media(c, 1))
        ws.cell(fila_media, C.MAT_VMAX).value = media(C.MAT_VMAX, 2)
        ws.cell(fila_media, C.MAT_PL).value = limpio(media(C.MAT_PL, 1))
        vaciar(ws.cell(fila_media, C.MAT_DUR))
    return fila_media


def estimar_por_fallo(ref_jugador, minutos, duracion, pl_por_metro=None):
    """Fallo de GPS con minutos conocidos: Real = REF / (1 + 0.9·(T−M)/M), redondeado
    (T = duración real del partido).
    Vel. máx no se estima; PL con el ratio PL/distancia del equipo en ese partido."""
    out = {m: (round(referencia.real_desde_ref(ref_jugador[m], minutos, duracion))
               if ref_jugador.get(m) is not None else None) for m in C.METRICS}
    out["vmax"] = None
    out["pl"] = round(out["distancia"] * pl_por_metro) if pl_por_metro and out["distancia"] else None
    out["dur"] = r1(minutos)
    return out


def pl_por_metro(datos):
    dist = sum(v["distancia"] for v in datos.values() if v.get("distancia") and v.get("pl"))
    pl = sum(v["pl"] for v in datos.values() if v.get("distancia") and v.get("pl"))
    return pl / dist if dist else None


def escribir_notas(ws, fila_media, lineas):
    """Notas bajo la tabla: fila media+2 en adelante (se reescriben enteras)."""
    base = fila_media + 2
    for i in range(6):
        vaciar(ws.cell(base + i, 1))
    for i, txt in enumerate(lineas):
        ws.cell(base + i, 1).value = txt


def marcar_cargado(ws):
    a2 = ws.cell(2, 1)
    if a2.value and "pendientes de cargar" in str(a2.value):
        a2.value = re.sub(r"\s*Datos pendientes de cargar tras el encuentro\.?", "", str(a2.value)).strip()


# ------------------------------------------------------------------ REF_PARTIDO
def _cargar_log():
    if os.path.exists(C.REF_LOG_JSON):
        with open(C.REF_LOG_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _guardar_log(log):
    with open(C.REF_LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)


def cuenta_para_ref(key):
    """Liga J2 en adelante (J1 excluido para siempre: GPS perdido, datos estimados)."""
    m = re.match(r"^J(\d+)$", key)
    return bool(m) and int(m.group(1)) >= 2


def actualizar_ref(wb_tipo, key, fecha, datos_reales, nombres, duracion):
    """REF_PARTIDO = media simple de sus componentes (pretemporada como 1 dato + cada partido
    con GPS real, extrapolado a la duración real T). Guarda el componente de este partido en
    ref_componentes.json (reprocesar lo sobrescribe: nunca cuenta dos veces) y reescribe la tabla.
    En el log queda la REF de ANTES de este partido (para su objetivo).
    Devuelve (actualizados [(dorsal, minutos)], cameos [(dorsal, minutos)]).
    """
    from . import ref_componentes as RC
    ws = wb_tipo["REF_PARTIDO"]
    filas = referencia.filas_ref(ws)
    comp = RC.cargar()
    if not comp:
        raise ValueError("Falta GPS/ref_componentes.json (componentes de la REF_PARTIDO)")
    for c in comp.values():                          # reproceso: fuera el componente anterior
        c.get("partidos", {}).pop(key, None)
    log = _cargar_log()
    previos, actualizados, cameos = {}, [], []
    for dor, d in sorted(datos_reales.items()):
        mins = d.get("min") or d.get("dur")          # minutos exactos del PDF si los hay
        if dor not in filas or not mins:
            continue
        c = comp.setdefault(str(dor), {"pretemporada": {m: num(ws.cell(filas[dor], 4 + i).value)
                                                        for i, m in enumerate(C.METRICS)},
                                       "partidos": {}})
        previos[str(dor)] = RC.ref_de(c, antes_de=fecha)
        c["partidos"][key] = {"fecha": fecha, "minutos": round(mins, 2), "duracion": round(duracion, 2),
                              "valores": {m: round(referencia.estimar(d[m], mins, duracion), 2)
                                          for m in C.METRICS}}
        actualizados.append((dor, mins))
        if mins < CAMEO_MIN:
            cameos.append((dor, mins))
    for dor, c in comp.items():
        if int(dor) in filas:
            ref = RC.ref_de(c)
            for i, m in enumerate(C.METRICS):
                ws.cell(filas[int(dor)], 4 + i).value = limpio(ref[m])
    RC.guardar(comp)
    log[key] = {"fecha": fecha, "aplicado": dt.datetime.now().isoformat(timespec="seconds"),
                "duracion": duracion, "previos": previos}
    _guardar_log(log)

    # nota de trazabilidad al final de la hoja (reemplaza la de este partido si ya existía)
    marca = f"[pipeline {key}]"
    fila_nota = None
    for r in range(1, ws.max_row + 1):
        if str(ws.cell(r, 1).value or "").startswith(marca):
            fila_nota = r
            break
    if fila_nota is None:
        fila_nota = ws.max_row + 2
    txt = (f"{marca} ACTUALIZACIÓN {fecha} ({key}): REF_PARTIDO = media simple de pretemporada (1 dato) "
           f"y cada partido de Liga (mismo peso), estimados a la duración real ({duracion:.1f}') con "
           f"fórmula de fatiga. {len(actualizados)} jugadores con GPS real: "
           + ", ".join(nombres.get(d, str(d)) for d, _ in actualizados) + ".")
    if cameos:
        txt += (" AVISO cameos cortos (extrapolación agresiva): "
                + ", ".join(f"{nombres.get(d, d)} ({mins:.0f}')" for d, mins in cameos) + ".")
    ws.cell(fila_nota, 1).value = txt
    return actualizados, cameos


# ------------------------------------------------------------- objetivo de partido
OBJ_COL0 = 14            # N: bloque "OBJETIVO" a la derecha de los datos (A-L no se tocan)
OBJ_CUMPL = OBJ_COL0 + len(C.METRICS)


def escribir_objetivos(ws, objetivos, nota, sin_valorar=()):
    """objetivos: {dorsal: {métrica: valor}}. sin_valorar: dorsales con datos estimados (fallo
    de GPS): tienen objetivo (para que la media compare el mismo grupo que la MEDIA EQUIPO real)
    pero sin semáforo ni cumplimiento. Escribe el bloque N-T y la media. Idempotente."""
    from .xlsx import pinta, semaforo
    filas, fila_media = filas_jugadores(ws)
    hdr = fila_cabecera_partido(ws)
    ws.cell(hdr - 1, OBJ_COL0).value = nota
    for i, m in enumerate(C.METRICS):
        ws.cell(hdr, OBJ_COL0 + i).value = f"Obj {C.METRIC_LABEL[m]}"
    ws.cell(hdr, OBJ_CUMPL).value = "Cumpl.\nmedio"
    cumpls = []
    for d, fila in filas.items():
        obj = objetivos.get(d)
        pcts = []
        for i, m in enumerate(C.METRICS):
            cell_o, cell_r = ws.cell(fila, OBJ_COL0 + i), ws.cell(fila, C.MAT_COL[m])
            real = num(cell_r.value)
            if obj and obj.get(m) is not None and real is not None:
                cell_o.value = limpio(obj[m])
                if d in sin_valorar:
                    pinta(cell_r, None)
                    continue
                pinta(cell_r, semaforo(real, obj[m]))
                if obj[m]:
                    pcts.append(real / obj[m] * 100)
            else:
                vaciar(cell_o)
                pinta(cell_r, None)
        c = ws.cell(fila, OBJ_CUMPL)
        if pcts:
            c.value = round(sum(pcts) / len(pcts))
            c.number_format = '0"%"'
            cumpls.append(sum(pcts) / len(pcts))
        else:
            vaciar(c)
    if fila_media:
        con = [filas[d] for d in objetivos if d in filas]
        for i, m in enumerate(C.METRICS):
            vals = [num(ws.cell(r, OBJ_COL0 + i).value) for r in con]
            vals = [v for v in vals if v is not None]
            ws.cell(fila_media, OBJ_COL0 + i).value = limpio(r1(sum(vals) / len(vals))) if vals else None
        c = ws.cell(fila_media, OBJ_CUMPL)
        c.value = round(sum(cumpls) / len(cumpls)) if cumpls else None
        c.number_format = '0"%"'
    return cumpls


def fila_cabecera_partido(ws):
    for r in range(1, 10):
        if ws.cell(r, 1).value == "Dorsal":
            return r
    raise ValueError(f"{ws.title}: sin cabecera")


def objetivos_por_minutos(ref_antes, datos, duracion):
    """{dorsal: objetivo} = REF previa al partido escalada a los minutos jugados."""
    from . import ref_historial
    out = {}
    for d, v in datos.items():
        o = ref_historial.objetivo_partido(ref_antes.get(d), v.get("min") or v.get("dur"), duracion)
        if o:
            out[d] = o
    return out
