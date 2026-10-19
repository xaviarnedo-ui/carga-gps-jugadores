"""REF_PARTIDO como MEDIA PONDERADA POR MINUTOS de sus componentes (desde el 19/10/2026; del 28/09
al 18/10 fue media simple):

  REF = Σ(peso · valor) / Σ(peso) de: bloque de pretemporada (peso 1, ya es la media de varios
        partidos) + estimado_T de cada partido de Liga con GPS real + otros partidos que el
        preparador pida contar (p. ej. con el filial).
  peso de un partido = minutos jugados / duración real del partido (máx. 1): un partido entero
  pesa 1 y un cameo de 20' en un partido de 100' pesa 0,2. Nadie se queda fuera.

GPS/ref_componentes.json guarda por jugador:
  {"<dorsal>": {"pretemporada": {métrica: v}, "partidos": {"J4": {"fecha": "...", "valores": {...}}}}}
Reprocesar un partido sobrescribe su componente (nunca cuenta dos veces).
"""
import json
import os

from . import config as C
from .xlsx import r1

RUTA = os.path.join(C.GPS_DIR, "ref_componentes.json")


def cargar():
    if os.path.exists(RUTA):
        with open(RUTA, encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar(comp):
    with open(RUTA, "w", encoding="utf-8") as f:
        json.dump(comp, f, ensure_ascii=False, indent=1)


def peso(partido):
    """Fracción del partido jugada (minutos / duración real, máx. 1). Sin minutos: 1."""
    mins, dur = partido.get("minutos"), partido.get("duracion")
    if not mins or not dur:
        return 1.0
    return min(mins / dur, 1.0)


def ref_de(comp_jugador, antes_de=None, sin=None):
    """Media ponderada por minutos de los componentes (pretemporada, peso 1).
    antes_de: solo partidos con fecha < antes_de. sin: excluir esa clave."""
    datos = [(1.0, comp_jugador["pretemporada"])] + [
        (peso(p), p["valores"]) for k, p in comp_jugador.get("partidos", {}).items()
        if k != sin and (antes_de is None or p["fecha"] < antes_de)]
    out = {}
    for m in C.METRICS:
        vals = [(w, d[m]) for w, d in datos if d.get(m) is not None]
        tot = sum(w for w, _ in vals)
        out[m] = r1(sum(w * v for w, v in vals) / tot) if vals and tot else None
    return out


def n_datos(comp_jugador):
    return 1 + len(comp_jugador.get("partidos", {}))
