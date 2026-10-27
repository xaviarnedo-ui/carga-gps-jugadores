"""Rutas y constantes compartidas del pipeline PDF → Excel → app."""
import os
import re

GPS_DIR = os.path.expanduser("~/Desktop/AT BALEARES 26-27/GPS")
MICRO_DIR = os.path.join(GPS_DIR, "Microciclos")
TIPO_XLSX = os.path.join(GPS_DIR, "Microciclo_Tipo.xlsx")
DISPO_XLSX = os.path.join(GPS_DIR, "Disponibilidad y Minutos.xlsx")
ESTADOS_JSON = os.path.join(GPS_DIR, "estados_jugadores.json")
REF_LOG_JSON = os.path.join(GPS_DIR, "pipeline_ref_log.json")
BACKUP_DIR = os.path.join(GPS_DIR, "_backups")
ARCHIVO_DIR = os.path.join(GPS_DIR, "_archivo")
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# orden fijo de los 6 bloques Obj/Real/Dif en las hojas de sesión y Acumulado
METRICS = ["distancia", "hmld", "hsr", "sprint", "acc", "dec"]
METRIC_LABEL = {"distancia": "Distancia", "hmld": "HMLD", "hsr": "HSR",
                "sprint": "Sprint", "acc": "ACC", "dec": "DEC"}

# --- layout hoja de sesión S##_GPS (columnas 1-based)
SES_OBJ_COL = {m: 4 + 3 * i for i, m in enumerate(METRICS)}   # Real = +1, Dif = +2
SES_VMAX, SES_PL, SES_DUR = 22, 23, 24
# --- layout hoja de partido / extra
MAT_COL = {m: 4 + i for i, m in enumerate(METRICS)}
MAT_VMAX, MAT_PL, MAT_DUR = 10, 11, 12

# --- semáforo de cumplimiento (fill, font)
AZUL = ("FFBDD7EE", "FF1F4E78")
VERDE = ("FFC6EFCE", "FF006100")
NARANJA = ("FFF8CBAD", "FFC55A11")
ROJO = ("FFFFC7CE", "FF9C0006")
AMARILLO = ("FFFFEB9C", "FF9C6500")
GRIS_MEDIA = "FFD9D9D9"

# estados de jugador en un día
#   nc = convocado, no jugó · noconv = no convocado (decisión técnica). Solo en partidos.
FULL, REHAB, LESION, DESCANSO, NC, NOCONV = "full", "rehab", "lesion", "descanso", "nc", "noconv"
ESTADOS = (FULL, REHAB, LESION, DESCANSO, NC, NOCONV)

# --- tolerancia del semáforo y pesos del % de cumplimiento (decisión del preparador, 27/10/2026)
# zona verde: ±10% Distancia/HMLD, ±20% HSR/ACC/DEC, ±2 sprints (valor absoluto); naranja hasta el
# doble de la tolerancia por encima, rojo más; azul por debajo. Mismo criterio en reglas.js.
TOLERANCIA = {"distancia": ("pct", 10), "hmld": ("pct", 10), "hsr": ("pct", 20),
              "acc": ("pct", 20), "dec": ("pct", 20), "sprint": ("abs", 2)}
PESOS_DIA = {"MD-4": {"acc": 2, "dec": 2}, "MD-3": {"hsr": 2, "sprint": 2}}

SHEET_KEY_RE = re.compile(r"^(S\d+\w*|PT\d+|J\d+|COPA\d+)_GPS$")


def is_match_key(key):
    return bool(re.match(r"^(PT|J|COPA)\d+$", key))
