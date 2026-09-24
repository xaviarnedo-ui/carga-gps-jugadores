"""Registro de lesiones (GPS/lesiones.json): una entrada por lesión.

  {"id": 3, "dorsal": 24, "tipo": "Rotura isquiotibial", "baja": "2026-08-30",
   "alta": "2026-09-19" | null, "nota": "..."}

Una lesión va de la baja hasta el primer día que vuelve a entrenar full (la etapa de rehab
va dentro). El pipeline la abre al pasar un jugador a lesión/rehab (pide el tipo) y la cierra
al volver a full.
"""
import json
import os

from . import config as C

RUTA = os.path.join(C.GPS_DIR, "lesiones.json")


def cargar(ruta=None):
    ruta = ruta or RUTA
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar(lista, ruta=None):
    with open(ruta or RUTA, "w", encoding="utf-8") as f:
        json.dump(sorted(lista, key=lambda l: (l["baja"], l["dorsal"])), f, ensure_ascii=False, indent=1)


def abierta(lista, dorsal):
    return next((l for l in lista if l["dorsal"] == int(dorsal) and not l.get("alta")), None)


def abrir(lista, dorsal, tipo, baja, nota=""):
    if abierta(lista, dorsal):
        raise ValueError(f"El dorsal {dorsal} ya tiene una lesión abierta")
    nueva = {"id": max((l["id"] for l in lista), default=0) + 1, "dorsal": int(dorsal),
             "tipo": tipo, "baja": baja, "alta": None, "nota": nota}
    lista.append(nueva)
    return nueva


def cerrar(lista, dorsal, alta):
    l = abierta(lista, dorsal)
    if l is None:
        raise ValueError(f"El dorsal {dorsal} no tiene ninguna lesión abierta")
    if alta < l["baja"]:
        raise ValueError(f"Alta {alta} anterior a la baja {l['baja']}")
    l["alta"] = alta
    return l
