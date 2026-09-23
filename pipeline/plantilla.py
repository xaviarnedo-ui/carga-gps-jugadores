"""Cruce de nombres del PDF ("MARTIN, ALVARO") con la plantilla de las hojas ("Martín, A.")."""
import unicodedata


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().replace(".", " ").split())


def clave(nombre):
    """'Martín, A.' y 'MARTIN, ALVARO' -> ('MARTIN', 'A')."""
    n = _norm(nombre)
    if "," in n:
        ape, resto = n.split(",", 1)
        resto = resto.strip()
        return ape.strip(), (resto[:1] if resto else "")
    return n, ""


def cruzar(nombres_pdf, plantilla, alias=None):
    """plantilla: {dorsal: nombre}. alias: {nombre_pdf_normalizado: dorsal}.

    Devuelve (asignados {nombre_pdf: dorsal}, sin_cruzar [nombre_pdf]).
    Falla si dos nombres del PDF caen en el mismo dorsal.
    """
    alias = {_norm(k): v for k, v in (alias or {}).items()}
    por_clave, por_ape = {}, {}
    for dor, nom in plantilla.items():
        ape, ini = clave(nom)
        por_clave[(ape, ini)] = dor
        por_ape.setdefault(ape, []).append(dor)
    asignados, sin = {}, []
    for n in nombres_pdf:
        if _norm(n) in alias:
            asignados[n] = alias[_norm(n)]
            continue
        ape, ini = clave(n)
        dor = por_clave.get((ape, ini))
        if dor is None and len(por_ape.get(ape, [])) == 1:
            dor = por_ape[ape][0]
        if dor is None:
            sin.append(n)
        else:
            asignados[n] = dor
    dup = {d for d in asignados.values() if list(asignados.values()).count(d) > 1}
    if dup:
        raise ValueError(f"Dos jugadores del PDF caen en el mismo dorsal: {sorted(dup)}")
    return asignados, sin
