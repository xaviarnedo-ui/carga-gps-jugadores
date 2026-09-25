"""Lectura del PDF "Informe de actividades" de Catapult.

La tabla "Desglose del deportista" sale como texto (una celda por línea); el donut de
participación y los bloques del período son imagen, por eso `render_resumen` los guarda
como PNG para que Claude los lea.
"""
import datetime as dt
import re
from dataclasses import dataclass, field
from typing import List, Optional

import fitz  # PyMuPDF

MESES = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
         "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "SETIEMBRE": 9, "OCTUBRE": 10,
         "NOVIEMBRE": 11, "DICIEMBRE": 12}
_NUM = re.compile(r"^-?\d+(\.\d+)?$")
_DUR = re.compile(r"^\d+:\d{2}:\d{2}$")


@dataclass
class FilaJugador:
    nombre: str            # tal cual el PDF, ya unido: "MARTIN, ALVARO"
    posicion: str
    distancia: float
    hmld: float
    hsr: float
    sprint: float
    acc: float
    dec: float
    vmax: float
    pl: float
    duracion: str          # "1:19:20"

    @property
    def minutos(self):
        return dur_a_min(self.duracion)

    @property
    def minutos_exactos(self):
        """Con segundos, sin redondear: para la fórmula de fatiga (en un cameo 8:49 ≠ 8,8')."""
        h, m, s = (int(x) for x in self.duracion.split(":"))
        return h * 60 + m + s / 60


@dataclass
class Informe:
    ruta: str
    titulo: str            # "S47", "J3 UCAM", "Rehab 15.9"
    etiqueta: str          # "MD-4", "MD", "Other"
    fecha: dt.date
    tiempo_total: Optional[str]
    filas: List[FilaJugador] = field(default_factory=list)
    medias: Optional[List[str]] = None
    paginas_resumen: List[int] = field(default_factory=list)

    @property
    def codigo(self):
        """Código de hoja deducido del título: 'S47', 'J3', 'PT9' o None (rehab/otros)."""
        m = re.match(r"^(S\d+\w*|PT\d+|J\d+)\b", self.titulo.strip(), re.I)
        return m.group(1).upper() if m else None


def dur_a_min(texto):
    """'1:19:20' -> 79.3 (minutos con 1 decimal). Acepta números ya en minutos."""
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return round(float(texto), 1)
    if isinstance(texto, dt.time):
        return round(texto.hour * 60 + texto.minute + texto.second / 60, 1)
    if isinstance(texto, dt.timedelta):
        return round(texto.total_seconds() / 60, 1)
    partes = str(texto).strip().split(":")
    try:
        nums = [int(float(x)) for x in partes]
    except ValueError:
        return None
    if len(nums) == 3:
        h, m, s = nums
    elif len(nums) == 2:        # "MM:SS" en algunas hojas antiguas
        h, (m, s) = 0, nums
    else:
        return round(float(nums[0]), 1)
    return round(h * 60 + m + s / 60, 1)


def _num(s):
    f = float(s)
    return int(f) if f == int(f) and "." not in s else f


def _parse_fecha(linea):
    # "MIÉRCOLES, SEPTIEMBRE 23, 2026 - 10:47:42 AM"
    m = re.search(r",\s*([A-ZÁÉÍÓÚÑ]+)\s+(\d{1,2}),\s*(\d{4})", linea.upper())
    if not m:
        raise ValueError(f"No reconozco la fecha del informe: {linea!r}")
    return dt.date(int(m.group(3)), MESES[m.group(1)], int(m.group(2)))


def _unir_nombre(partes):
    nombre = ""
    for p in partes:
        p = p.strip()
        if nombre.endswith("-"):
            nombre = nombre[:-1] + p        # "AL-" + "VARO"
        elif nombre:
            nombre += " " + p
        else:
            nombre = p
    return re.sub(r"\s+", " ", nombre).replace(" ,", ",")


def leer(ruta) -> Informe:
    doc = fitz.open(ruta)
    p1 = [l.strip() for l in doc[0].get_text().splitlines() if l.strip()]
    # cabecera: título, [etiqueta MD-x], fecha (a veces el informe no trae etiqueta)
    i_fecha = next(i for i, l in enumerate(p1[:6]) if re.search(r",\s*\d{4}\s*-", l))
    titulo, fecha = p1[1], _parse_fecha(p1[i_fecha])
    etiqueta = p1[2] if i_fecha == 3 else ""
    tiempo_total = None
    if "TIEMPO TOTAL" in p1:
        tiempo_total = p1[p1.index("TIEMPO TOTAL") + 1]

    inf = Informe(ruta=str(ruta), titulo=titulo, etiqueta=etiqueta, fecha=fecha,
                  tiempo_total=tiempo_total)
    for i, page in enumerate(doc):
        lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
        if "Desglose del deportista" not in lines:
            inf.paginas_resumen.append(i)
            continue
        body = lines[lines.index("Duration") + 1:]
        pendientes = []
        j = 0
        while j < len(body):
            tok = body[j]
            if tok == "Averages":
                inf.medias = body[j + 1:j + 10]
                break
            # una fila = [nombre..., posición, 8 números, duración]
            ventana = body[j:j + 9]
            if (len(ventana) == 9 and all(_NUM.match(t) for t in ventana[:8])
                    and _DUR.match(ventana[8]) and pendientes):
                *nom, pos = pendientes
                v = [_num(t) for t in ventana[:8]]
                inf.filas.append(FilaJugador(_unir_nombre(nom), pos, *v, ventana[8]))
                pendientes = []
                j += 9
                continue
            pendientes.append(tok)
            j += 1
    if not inf.filas:
        raise ValueError(f"No encuentro la tabla 'Desglose del deportista' en {ruta}")
    return inf


def render_resumen(inf: Informe, carpeta, dpi=80):
    """Guarda como PNG las páginas de resumen (donut de participación, bloques)."""
    import os
    os.makedirs(carpeta, exist_ok=True)
    doc = fitz.open(inf.ruta)
    rutas = []
    base = re.sub(r"[^\w.-]+", "_", inf.titulo)
    for i in inf.paginas_resumen:
        out = os.path.join(carpeta, f"{base}_p{i + 1}.png")
        doc[i].get_pixmap(dpi=dpi).save(out)
        rutas.append(out)
    return rutas
