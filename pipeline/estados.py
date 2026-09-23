"""Estado de cada jugador (full / rehab / lesión) y registro por sesión.

Vive en GPS/estados_jugadores.json (fuera del repo: es dato médico del club).
  vigente:  {"4": {"estado": "lesion", "desde": "2026-09-17", "nota": "..."}}
  sesiones: {"S47": {"fecha": "2026-09-23", "estados": {"2": "full", "6": "descanso", ...}}}
  historial: [{"fecha", "dorsal", "de", "a", "nota"}]
"descanso" y "nc" (convocado, no jugó) son de un solo día: no cambian el vigente.
"""
import json
import os

from . import config as C

PERSISTENTES = (C.FULL, C.REHAB, C.LESION)


def cargar(ruta=None):
    ruta = ruta or C.ESTADOS_JSON
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return {"vigente": {}, "sesiones": {}, "historial": []}


def guardar(data, ruta=None):
    ruta = ruta or C.ESTADOS_JSON
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def vigente(data, dorsal):
    return data["vigente"].get(str(dorsal), {}).get("estado", C.FULL)


def cambiar(data, dorsal, estado, fecha, nota=""):
    """Cambia el estado vigente (solo full/rehab/lesion). Devuelve el estado anterior."""
    if estado not in PERSISTENTES:
        return vigente(data, dorsal)
    antes = vigente(data, dorsal)
    if antes != estado:
        data["historial"].append({"fecha": fecha, "dorsal": int(dorsal),
                                  "de": antes, "a": estado, "nota": nota})
    data["vigente"][str(dorsal)] = {"estado": estado, "desde": fecha if antes != estado
                                    else data["vigente"].get(str(dorsal), {}).get("desde", fecha),
                                    "nota": nota}
    return antes


def registrar_sesion(data, key, fecha, estados_dia):
    data["sesiones"][key] = {"fecha": fecha,
                             "estados": {str(d): e for d, e in sorted(estados_dia.items())}}
