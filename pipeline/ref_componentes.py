"""REF_PARTIDO como MEDIA SIMPLE de sus componentes (desde el 28/09/2026):

  REF = media( bloque de pretemporada (1 dato) , estimado_T de cada partido de Liga con GPS real ,
               otros partidos que el preparador pida contar, p. ej. con el filial )

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


def ref_de(comp_jugador, antes_de=None, sin=None):
    """Media de los componentes. antes_de: solo partidos con fecha < antes_de. sin: excluir esa clave."""
    datos = [comp_jugador["pretemporada"]] + [
        p["valores"] for k, p in comp_jugador.get("partidos", {}).items()
        if k != sin and (antes_de is None or p["fecha"] < antes_de)]
    out = {}
    for m in C.METRICS:
        vals = [d[m] for d in datos if d.get(m) is not None]
        out[m] = r1(sum(vals) / len(vals)) if vals else None
    return out


def n_datos(comp_jugador):
    return 1 + len(comp_jugador.get("partidos", {}))
