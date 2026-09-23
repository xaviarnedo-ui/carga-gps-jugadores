"""Hoja de sesión de entrenamiento S##_GPS: Real/Dif/semáforo, MEDIA EQUIPO, notas,
y propagación de los cambios de estado a los Objetivos del resto de la semana."""
import re

from . import config as C
from .xlsx import (BLANCO, filas_jugadores, fecha_hoja, limpio, num, pinta, r1,
                   semaforo, vaciar)
from . import referencia


def es_hoja_sesion(nombre):
    return bool(re.match(r"^S\d+\w*_GPS$", nombre))


def hojas_sesion(wb):
    """[(key, ws, fecha)] de las hojas S##_GPS, en orden cronológico."""
    out = [(n[:-4], wb[n], fecha_hoja(wb[n])) for n in wb.sheetnames if es_hoja_sesion(n)]
    return sorted(out, key=lambda t: (t[2], t[0]))


def tipo_y_dia(ws):
    """'MICROCICLO 11 · TIPO B · MD-4' -> ('B', 'MD-4')."""
    a3 = str(ws.cell(3, 1).value or "").upper()
    mt = re.search(r"TIPO ([A-Z])", a3)
    md = re.search(r"(MD[+-]\d)", a3)
    return (mt.group(1) if mt else None), (md.group(1) if md else None)


def hecha(ws):
    filas, _ = filas_jugadores(ws)
    return any(num(ws.cell(r, C.SES_PL).value) is not None
               or any(num(ws.cell(r, c + 1).value) is not None for c in C.SES_OBJ_COL.values())
               for r in filas.values())


def objetivo_fila(ws, fila):
    return {m: num(ws.cell(fila, c).value) for m, c in C.SES_OBJ_COL.items()}


def tiene_objetivo(ws, fila):
    return any(v is not None for v in objetivo_fila(ws, fila).values())


def _escribe_obj(ws, fila, obj):
    for m, c in C.SES_OBJ_COL.items():
        cell = ws.cell(fila, c)
        if obj is None or obj.get(m) is None:
            vaciar(cell)
        else:
            cell.value = limpio(obj[m])
            cell.fill = BLANCO


def ajustar_objetivos(wb, desde_key, dorsal, estado, ref, coefs, rol_md1=None):
    """Aplica un cambio de estado desde la sesión `desde_key` en adelante (no retroactivo).

    - rehab / lesión: sin Objetivo ese día y el resto de la semana.
    - full: Objetivo = REF × coeficiente del día, ese día y el resto de la semana.
    - descanso: sin Objetivo solo ese día.
    Devuelve la lista de sesiones tocadas.
    """
    tocadas, empezado = [], False
    for key, ws, _ in hojas_sesion(wb):
        empezado = empezado or key == desde_key
        if not empezado:
            continue                                  # sesiones anteriores: no se tocan
        if key != desde_key and hecha(ws):
            continue                                  # nunca reescribir una sesión ya cargada
        filas, _ = filas_jugadores(ws)
        if dorsal not in filas:
            continue
        fila = filas[dorsal]
        if estado in (C.REHAB, C.LESION) or (estado == C.DESCANSO and key == desde_key):
            _escribe_obj(ws, fila, None)
        elif estado == C.FULL:
            tipo, dia = tipo_y_dia(ws)
            if dia == "MD+1":
                if rol_md1 not in ("T", "S"):
                    raise ValueError(f"{key} es MD+1: indica si {dorsal} cuenta como titular o suplente")
                dia = "MD+1" + rol_md1
            if tipo not in coefs or dia not in coefs[tipo]:
                raise ValueError(f"{key}: no hay coeficientes para Tipo {tipo} / {dia}")
            if dorsal not in ref:
                raise ValueError(f"Dorsal {dorsal} sin REF_PARTIDO: no puedo calcular su objetivo")
            _escribe_obj(ws, fila, referencia.objetivo(ref[dorsal], coefs[tipo][dia]))
        tocadas.append(key)
        if estado == C.DESCANSO:
            break
    return tocadas


def rellenar(ws, datos, estados_dia):
    """datos: {dorsal: {métricas..., vmax, pl, dur}} · estados_dia: {dorsal: estado}.

    full  -> Real + Dif + semáforo (necesita Objetivo)
    rehab -> solo Real (sin Obj/Dif/semáforo), informativo
    lesión / descanso -> fila vacía
    """
    filas, fila_media = filas_jugadores(ws)
    fuera = sorted(set(datos) - set(filas))
    if fuera:
        raise ValueError(f"{ws.title}: dorsales del PDF que no están en la hoja: {fuera}")
    for dorsal, fila in filas.items():
        est = estados_dia.get(dorsal)
        d = datos.get(dorsal)
        if est in (C.FULL, C.REHAB) and d is None:
            raise ValueError(f"{ws.title}: {dorsal} marcado '{est}' pero no está en el PDF")
        if est not in (C.FULL, C.REHAB) and d is not None:
            raise ValueError(f"{ws.title}: {dorsal} está en el PDF pero marcado '{est}'")
        if est == C.FULL and not tiene_objetivo(ws, fila):
            raise ValueError(f"{ws.title}: {dorsal} es full pero no tiene Objetivo "
                             f"(¿vuelve de rehab/lesión? usa --estado {dorsal}=full)")
        if est == C.REHAB:
            _escribe_obj(ws, fila, None)
        obj = objetivo_fila(ws, fila)
        for m, c in C.SES_OBJ_COL.items():
            real_c, dif_c = ws.cell(fila, c + 1), ws.cell(fila, c + 2)
            if d is None:
                vaciar(real_c), vaciar(dif_c)
                pinta(real_c, None), pinta(dif_c, None)
                continue
            real_c.value = d[m]
            if est == C.FULL and obj[m] is not None:
                dif_c.value = limpio(r1(d[m] - obj[m]))
                color = semaforo(d[m], obj[m])
            else:
                vaciar(dif_c)
                color = None
            pinta(real_c, color), pinta(dif_c, color)
        for col, k in ((C.SES_VMAX, "vmax"), (C.SES_PL, "pl"), (C.SES_DUR, "dur")):
            cell = ws.cell(fila, col)
            if d is None or d.get(k) is None:
                vaciar(cell)
            else:
                cell.value = d[k]
    escribir_media(ws, filas, fila_media, estados_dia)
    return fila_media


def escribir_media(ws, filas, fila_media, estados_dia):
    """MEDIA EQUIPO solo sobre los jugadores full del día."""
    full = [filas[d] for d, e in estados_dia.items() if e == C.FULL and d in filas]

    def media(col, dec):
        vals = [num(ws.cell(r, col).value) for r in full]
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), dec) if vals else None

    for m, c in C.SES_OBJ_COL.items():
        o, r = media(c, 1), media(c + 1, 1)
        ws.cell(fila_media, c).value = limpio(o)
        ws.cell(fila_media, c + 1).value = limpio(r)
        ws.cell(fila_media, c + 2).value = limpio(r1(r - o)) if o is not None and r is not None else None
        color = semaforo(r, o)
        pinta(ws.cell(fila_media, c + 1), color), pinta(ws.cell(fila_media, c + 2), color)
    ws.cell(fila_media, C.SES_VMAX).value = media(C.SES_VMAX, 2)
    ws.cell(fila_media, C.SES_PL).value = limpio(media(C.SES_PL, 1))
    vaciar(ws.cell(fila_media, C.SES_DUR))


def nota_estados(nombres, estados_dia, extra=""):
    grupos = {C.REHAB: [], C.LESION: [], C.DESCANSO: []}
    for d, e in sorted(estados_dia.items()):
        if e in grupos:
            grupos[e].append(nombres.get(d, str(d)))
    partes = []
    if grupos[C.REHAB]:
        partes.append("Rehab (informativo, sin objetivo; no cuenta para la MEDIA EQUIPO, sí para "
                      "Acumulado individual y ACWR): " + " · ".join(grupos[C.REHAB]))
    if grupos[C.LESION]:
        partes.append("Lesionados / no disponibles (sin sesión ni objetivo): "
                      + " · ".join(grupos[C.LESION]))
    if grupos[C.DESCANSO]:
        partes.append("Descanso / gestión de carga (sin sesión ni objetivo hoy, sigue disponible): "
                      + " · ".join(grupos[C.DESCANSO]))
    txt = " ".join(p if p.endswith(".") else p + "." for p in partes)   # "Fontanet, B." ya acaba en punto
    return (txt + " " + extra).strip() or None


def escribir_notas(ws, fila_media, texto):
    """Fila media+2 = estados del día (la media+1 describe el objetivo y no se toca)."""
    cell = ws.cell(fila_media + 2, 1)
    cell.value = texto
