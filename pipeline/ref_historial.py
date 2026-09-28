"""REF_PARTIDO vigente justo ANTES de cada partido, y objetivo de partido por jugador.

Se reconstruye hacia atrás desde la REF actual deshaciendo cada actualización:
  - partidos aplicados por el pipeline: pipeline_ref_log.json guarda los valores previos (exacto);
  - J2/J3 (recalculados en bloque): REF_antes = 2·REF_después − Estimado_T (±0,1 por redondeos).

Objetivo de partido = lo que habría hecho con su REF de antes del partido en los minutos que
jugó: REF / (1 + 0,9·(T − M)/M), con T = duración real de ese partido (fórmula de fatiga inversa).
"""
from . import config as C
from . import referencia as R
from .xlsx import r1


def ref_antes(ref_actual, eventos, log):
    """eventos: [(fecha_iso, key, {dorsal: (valores, minutos)}, T)] de los partidos/Extra que
    actualizaron la REF. Devuelve {key: {dorsal: {métrica: valor}}}."""
    ref = {d: {m: v.get(m) for m in C.METRICS} for d, v in ref_actual.items()}
    out = {}
    for fecha, key, reales, T in sorted(eventos, key=lambda e: e[0], reverse=True):
        entrada = log.get(key) or {}
        if entrada.get("previos"):
            for d, prev in entrada["previos"].items():
                ref[int(d)] = {m: prev.get(m) for m in C.METRICS}
        elif entrada.get("bloqueado"):
            T = entrada.get("duracion") or T
            for d, (vals, mins) in reales.items():
                if d not in ref:
                    continue
                ref[d] = {m: (r1(2 * ref[d][m] - R.estimar(vals[m], mins, T))
                              if ref[d][m] is not None and vals.get(m) is not None else ref[d][m])
                          for m in C.METRICS}
        out[key] = {d: dict(v) for d, v in ref.items()}
    return out


def objetivo_partido(ref_jugador, minutos, T):
    if not ref_jugador or not minutos or not T:
        return None
    return {m: (r1(R.real_desde_ref(ref_jugador[m], minutos, T)) if ref_jugador.get(m) is not None else None)
            for m in C.METRICS}
