"""Del PDF a {dorsal: valores} usando la plantilla de una hoja."""
from . import pdf_catapult, plantilla


def valores(fila):
    return {"distancia": fila.distancia, "hmld": fila.hmld, "hsr": fila.hsr,
            "sprint": fila.sprint, "acc": fila.acc, "dec": fila.dec,
            "vmax": fila.vmax, "pl": fila.pl, "dur": fila.minutos, "min": fila.minutos_exactos}


def datos_por_dorsal(inf, nombres_hoja, alias=None):
    """-> ({dorsal: valores}, sin_cruzar)."""
    asign, sin = plantilla.cruzar([f.nombre for f in inf.filas], nombres_hoja, alias)
    return {asign[f.nombre]: valores(f) for f in inf.filas if f.nombre in asign}, sin


def leer(ruta):
    """PDF de Catapult o, si Catapult no genera el PDF, un .csv con la tabla "Desglose del deportista"
    copiada a mano (ver leer_csv)."""
    if str(ruta).lower().endswith(".csv"):
        return leer_csv(ruta)
    return pdf_catapult.leer(ruta)


def leer_csv(ruta):
    """CSV de respaldo: líneas `titulo,S75` · `fecha,2026-10-31` · `etiqueta,MD-1` y, tras la cabecera
    `nombre,posicion,distancia,hmld,hsr,sprint,acc,dec,vmax,pl,duracion`, una fila por jugador con el
    nombre como en Catapult ("APELLIDO, NOMBRE") y la duración h:mm:ss."""
    import csv
    import datetime as dt
    meta, filas, cab = {}, [], None
    with open(ruta, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            if cab is None and row[0].strip().lower() == "nombre":
                cab = [c.strip().lower() for c in row]
                continue
            if cab is None:
                meta[row[0].strip().lower()] = row[1].strip()
                continue
            d = dict(zip(cab, (c.strip() for c in row)))
            filas.append(pdf_catapult.FilaJugador(
                nombre=d["nombre"].upper(), posicion=d.get("posicion", ""),
                **{k: float(d[k].replace(",", ".")) for k in ("distancia", "hmld", "hsr", "sprint", "acc", "dec", "vmax", "pl")},
                duracion=d["duracion"]))
    return pdf_catapult.Informe(ruta=str(ruta), titulo=meta["titulo"], etiqueta=meta.get("etiqueta", ""),
                                fecha=dt.date.fromisoformat(meta["fecha"]), tiempo_total=None, filas=filas)
