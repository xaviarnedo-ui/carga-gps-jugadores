"""REF_PARTIDO y coeficientes (Microciclo_Tipo.xlsx) + fórmulas de fatiga."""
import re

from . import config as C
from .xlsx import num, r1

# columnas de la hoja MICROCICLOS: B..G
DIAS = ["MD+1S", "MD+1T", "MD-4", "MD-3", "MD-2", "MD-1"]
FILA_METRICA = {"DISTANCIA": "distancia", "HMLD": "hmld", "HSR": "hsr",
                "SPRINT": "sprint", "ACC": "acc", "DEC": "dec"}
FATIGA = 0.90


def coeficientes(wb_tipo):
    """-> {'B': {'MD-4': {'distancia': 0.5, ...}, ...}, ...}"""
    ws = wb_tipo["MICROCICLOS"]
    out, tipo = {}, None
    for r in range(1, ws.max_row + 1):
        a = str(ws.cell(r, 1).value or "").strip().upper()
        m = re.match(r"MICROCICLO TIPO ([A-Z])", a)
        if m:
            tipo = m.group(1)
            out[tipo] = {d: {} for d in DIAS}
        elif tipo and a in FILA_METRICA:
            for j, d in enumerate(DIAS):
                out[tipo][d][FILA_METRICA[a]] = num(ws.cell(r, 2 + j).value)
    return out


def filas_ref(ws):
    """{dorsal: fila} de la hoja REF_PARTIDO."""
    out = {}
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if isinstance(v, int) and ws.cell(r, 4).value is not None:
            out[v] = r
    return out


def ref_partido(wb_tipo):
    ws = wb_tipo["REF_PARTIDO"]
    return {d: {m: num(ws.cell(r, 4 + i).value) for i, m in enumerate(C.METRICS)}
            for d, r in filas_ref(ws).items()}


def objetivo(ref_jugador, coef_dia):
    """round(REF × coef, 1) por métrica. None si no hay referencia."""
    if not ref_jugador:
        return None
    return {m: (r1(ref_jugador[m] * coef_dia[m]) if ref_jugador.get(m) is not None else None)
            for m in C.METRICS}


def estimar_95(real, minutos):
    """Estimado_95 = Real + (95 − M) × (Real / M) × 0.90 ; sin extrapolar si M ≥ 95."""
    if real is None or not minutos:
        return None
    if minutos >= 95:
        return real
    return real + (95 - minutos) * (real / minutos) * FATIGA


def real_desde_ref(ref_valor, minutos):
    """Inversa: Real_estimado = REF / (1 + 0.90 × (95 − M) / M)."""
    if ref_valor is None or not minutos:
        return None
    if minutos >= 95:
        return ref_valor
    return ref_valor / (1 + FATIGA * (95 - minutos) / minutos)
