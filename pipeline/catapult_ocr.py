"""Lector por OCR de los PDF de Catapult de la temporada 25-26 (texto codificado, no se puede
extraer con PyMuPDF). OCR con Apple Vision vía pyobjc 10.3.1 (instalado con pip --user; swiftc
está roto en este Mac). Cada columna se lee por separado a 400 ppp; los huecos de sprints y
ACC+DEC se releen con la columna de la izquierda o la celda sola a 700 ppp. Al final se comprueba
contra la fila «Averages» del propio PDF: `chk` = desvío % de la suma frente a media × n."""
import os
import re
import tempfile

import fitz

# posición x relativa del centro de cada columna, según el diseño de la tabla
COLS_A = {"distancia": .309, "hmld": .404, "hsr": .497, "sprint": .596, "accdec": .69, "vmax": .787, "pl": .881}
COLS_B = {"distancia": .285, "hmld": .371, "hsr": .457, "sprint": .542, "accdec": .629, "vmax": .714, "pl": .80,
          "dur": .887}  # con Duration y Player Load
COLS_C = {"distancia": .309, "hmld": .405, "hsr": .497, "accdec": .596, "sprint": .69, "vmax": .787,
          "dur": .881}  # con Duration, sin Player Load
METRICAS = ["distancia", "hmld", "hsr", "sprint", "accdec", "vmax", "pl", "dur"]
MESES = {"ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
         "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12}
_TMP = os.path.join(tempfile.gettempdir(), "catapult_ocr_crop.png")


def ocr(path):
    """[[texto, x, y, w, h], ...] relativos a la imagen, y medida desde arriba."""
    import Quartz
    import Vision
    from Foundation import NSURL
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(path), None)
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(False)
    Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None).performRequests_error_([req], None)
    out = []
    for o in req.results() or []:
        b = o.boundingBox()
        out.append([str(o.topCandidates_(1)[0].string()), b.origin.x, 1 - b.origin.y - b.size.height,
                    b.size.width, b.size.height])
    return out


def _num(t):
    t = (t.replace(",", ".").replace("O", "0").replace("o", "0").replace("l", "1").replace("I", "1")
         .replace(" ", "").strip())
    return float(t) if re.fullmatch(r"\d+(\.\d+)?", t) else None


def _durnum(t):
    m = re.fullmatch(r"(\d+)[:.](\d\d)[:.](\d\d)", t.replace(" ", ""))
    return int(m[1]) * 60 + int(m[2]) + int(m[3]) / 60 if m else None


def _ocr_recorte(page, rect, dpi, margen=0):
    page.get_pixmap(dpi=dpi, clip=rect).save(_TMP)
    if margen:
        from PIL import Image, ImageOps
        ImageOps.expand(Image.open(_TMP), border=margen, fill="white").save(_TMP)
    return ocr(_TMP)


def _pagina(page):
    page.get_pixmap(dpi=300).save(_TMP)
    it = ocr(_TMP)
    if not any("Desglose del deportista" in t for t, *_ in it):
        return None
    tx = [t.strip() for t, *_ in it]
    cols = COLS_A if "Duration" not in tx else COLS_B if any("Player Load" in t for t in tx) else COLS_C
    ancho = .04 if cols is COLS_B else .045
    nombres = sorted([(y, t, x) for t, x, y, w, h in it if x < .17 and y > .22 and (
        ("," in t and re.search(r"[A-ZÁÉÍÓÚÑ]{2,}", t)) or t.strip() == "Averages")])
    W, H = page.rect.width, page.rect.height
    colvals = {}
    for c, cx in cols.items():
        f = _durnum if c == "dur" else _num
        res = _ocr_recorte(page, fitz.Rect((cx - ancho) * W, .22 * H, (cx + ancho) * W, .98 * H), 400)
        colvals[c] = [(.22 + (y + h / 2) * .76, f(t)) for t, x, y, w, h in res if f(t) is not None]
    filas = []
    for i, (y, t, x) in enumerate(nombres):
        y1 = nombres[i + 1][0] - .006 if i + 1 < len(nombres) else y + .055
        nm = t
        for tt, xx, yy, ww, hh in it:   # nombres partidos en dos líneas
            if xx < .17 and y < yy < y1 and tt.strip() != "Averages" and not re.fullmatch(r"(D|M|DL|DC|POR)", tt):
                nm += " " + tt
        r = {"nombre": re.sub(r"-\s+", "", nm)}
        for c, vals in colvals.items():
            cand = [v for yy, v in vals if y - .01 <= yy < y1 + .004]
            if cand:
                r[c] = cand[0]
                continue
            if c in ("sprint", "accdec"):   # 2.ª pasada: junto a la columna de la izquierda (cifras sueltas)
                orden = sorted(cols, key=cols.get)
                izq = orden[orden.index(c) - 1]
                res = sorted(_ocr_recorte(page, fitz.Rect((cols[izq] - .04) * W, (y - .012) * H, (cols[c] + .04) * W,
                                                          min(y1, y + .04) * H), 500, 80), key=lambda a: a[1])
                nums = [_num(t2) for t, *_ in res for t2 in t.split() if _num(t2) is not None]
                if len(nums) >= 2:
                    r[c] = nums[-1]
                    continue
            f = _durnum if c == "dur" else _num   # 3.ª pasada: la celda sola, ampliada y con margen
            vs = [f(t) for t, *_ in _ocr_recorte(page, fitz.Rect((cols[c] - .04) * W, (y - .012) * H,
                                                                (cols[c] + .04) * W, min(y1, y + .04) * H), 700, 120)
                  if f(t) is not None]
            if vs:
                r[c] = vs[0]
        filas.append(r)
    return filas


def cabecera(ruta):
    """Texto de la cabecera de la primera página (fecha, etiqueta MD, TIEMPO TOTAL)."""
    doc = fitz.open(ruta)
    doc[0].get_pixmap(dpi=200).save(_TMP)
    return " ".join(t for t, x, y, w, h in sorted(ocr(_TMP), key=lambda a: (round(a[2], 2), a[1])) if y < .12)


def fecha_de(head):
    m = re.search(r"(%s) (\d+), ?(\d{4})" % "|".join(MESES), head.upper())
    return f"{int(m[3]):04d}-{MESES[m[1]]:02d}-{int(m[2]):02d}" if m else None


def etiqueta_de(head, key):
    """«S36 MD-S» → MD-5 (el OCR confunde 5 y S); «S61 MD4» → MD-4; sin etiqueta → None."""
    m = re.search(re.escape(key) + r"\s+(MD\s*[-+]?\s*[0-9S]?)(?=\s|$)", head)
    if not m or m[1].strip() == "MD":
        return None
    e = m[1].replace(" ", "").replace("S", "5")
    return re.sub(r"^MD(\d)", r"MD-\1", e)


def completar(rows, avg):
    """Si en una columna falta un único valor, sale de la fila de medias. Devuelve el desvío %
    de cada columna frente a la fila «Averages» (0,0 = la lectura cuadra)."""
    chk = {}
    for c in METRICAS:
        if c not in avg:
            continue
        falta = [r for r in rows if c not in r]
        tot = avg[c] * len(rows)
        s = sum(r[c] for r in rows if c in r)
        if not falta and tot and abs(s - tot) / tot > (.1 if c == "sprint" else .05):
            # la fila «Averages» mal leída (cifra cortada, columnas corridas): no sirve de control
            avg.pop(c)
            chk[c] = None
            continue
        if len(falta) == 1 and c != "vmax":
            falta[0][c] = round(tot - s, 1 if c == "dur" else 0)
            falta[0].setdefault("_imp", []).append(c)
            s = tot
        chk[c] = round((s - tot) / tot * 100, 1) if tot else 0
    return chk


def leer(ruta):
    """Lee un PDF entero: {head, fecha, etiqueta, total, rows, avg, chk}."""
    key = os.path.splitext(os.path.basename(ruta))[0]
    doc = fitz.open(ruta)
    head = cabecera(ruta)
    filas = []
    for i, pg in enumerate(doc):
        if i:
            filas += _pagina(pg) or []
    rows = [r for r in filas if r["nombre"] != "Averages"]
    avg = next((r for r in filas if r["nombre"] == "Averages"), {})
    m = re.search(r"TIEMPO TOTAL (\d+):(\d+):(\d+)", head)
    return dict(head=head, fecha=fecha_de(head), etiqueta=etiqueta_de(head, key), rows=rows, avg=avg,
                chk=completar(rows, avg), total=int(m[1]) * 60 + int(m[2]) + int(m[3]) / 60 if m else None)
