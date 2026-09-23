"""Del PDF a {dorsal: valores} usando la plantilla de una hoja."""
from . import pdf_catapult, plantilla


def valores(fila):
    return {"distancia": fila.distancia, "hmld": fila.hmld, "hsr": fila.hsr,
            "sprint": fila.sprint, "acc": fila.acc, "dec": fila.dec,
            "vmax": fila.vmax, "pl": fila.pl, "dur": fila.minutos}


def datos_por_dorsal(inf, nombres_hoja, alias=None):
    """-> ({dorsal: valores}, sin_cruzar)."""
    asign, sin = plantilla.cruzar([f.nombre for f in inf.filas], nombres_hoja, alias)
    return {asign[f.nombre]: valores(f) for f in inf.filas if f.nombre in asign}, sin


def leer(ruta):
    return pdf_catapult.leer(ruta)
