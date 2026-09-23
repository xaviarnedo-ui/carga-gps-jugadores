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


def estimar_por_fallo(ref_jugador, minutos, pl_por_metro=None):
    """Fallo de GPS con minutos conocidos: Real = REF / (1 + 0.9·(95−M)/M), redondeado.
    Vel. máx no se estima; PL con el ratio PL/distancia del equipo en ese partido."""
    out = {m: (round(referencia.real_desde_ref(ref_jugador[m], minutos))
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


def actualizar_ref(wb_tipo, key, fecha, datos_reales, nombres):
    """nuevo = round((anterior + estimado_95) / 2, 1) para quien jugó con GPS real.

    Guarda los valores previos en pipeline_ref_log.json: si el partido ya se había aplicado,
    primero se deshace (reprocesar nunca promedia dos veces).
    Devuelve (actualizados [(dorsal, minutos)], cameos [(dorsal, minutos)]).
    """
    ws = wb_tipo["REF_PARTIDO"]
    filas = referencia.filas_ref(ws)
    log = _cargar_log()
    if key in log:                                   # deshacer la aplicación anterior
        for dor, prev in log[key]["previos"].items():
            for i, m in enumerate(C.METRICS):
                ws.cell(filas[int(dor)], 4 + i).value = prev[m]
    previos, actualizados, cameos = {}, [], []
    for dor, d in sorted(datos_reales.items()):
        if dor not in filas or not d.get("dur"):
            continue
        fila = filas[dor]
        prev = {m: num(ws.cell(fila, 4 + i).value) for i, m in enumerate(C.METRICS)}
        previos[str(dor)] = prev
        for i, m in enumerate(C.METRICS):
            est = referencia.estimar_95(d[m], d["dur"])
            if prev[m] is None:
                nuevo = r1(est)
            else:
                nuevo = r1((prev[m] + est) / 2)
            ws.cell(fila, 4 + i).value = limpio(nuevo)
        actualizados.append((dor, d["dur"]))
        if d["dur"] < CAMEO_MIN:
            cameos.append((dor, d["dur"]))
    log[key] = {"fecha": fecha, "aplicado": dt.datetime.now().isoformat(timespec="seconds"),
                "previos": previos}
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
    txt = (f"{marca} ACTUALIZACIÓN {fecha} ({key}): REF_PARTIDO = media(valor anterior, "
           f"estimación a 95' con fórmula de fatiga) para {len(actualizados)} jugadores con GPS "
           f"real: " + ", ".join(nombres.get(d, str(d)) for d, _ in actualizados) + ".")
    if cameos:
        txt += (" AVISO cameos cortos (extrapolación agresiva, ya pesan el 50% de su referencia): "
                + ", ".join(f"{nombres.get(d, d)} ({mins:.0f}')" for d, mins in cameos) + ".")
    ws.cell(fila_nota, 1).value = txt
    return actualizados, cameos
