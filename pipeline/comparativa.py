"""Comparativa de carga GPS entre la temporada pasada (25-26) y esta (26-27), por tipo de día,
siempre sobre las MISMAS jornadas (J1…JN de cada temporada). Se repite a lo largo del año.

- 25-26: los PDF de Catapult de PROFESIONAL/…/AT BALEARES 25-26/GPS se leen por OCR
  (`catapult_ocr`) solo la primera vez; lo leído se guarda en
  GPS/Comparativa temporadas/Temporada 25-26.json (fuera del repo, que es público).
- 26-27: las hojas *_GPS de los Microciclo N.xlsx.
- Salida: HTML en GPS/Comparativa temporadas/ y PDF en GPS/Informes/.

Reglas (las de la primera comparativa, 04/11/2026, iguales en las dos temporadas):
- Ventana: del día siguiente al último amistoso (PT) antes de J1 hasta el día de JN.
- Sesión: media de los jugadores con distancia ≥ 60 % de la mediana del día (sesión completa).
- Partido: jugadores con ≥ 75 % de la distancia del que más corrió (Liga + Copa).
- MD+1: el año pasado el GPS solo lo llevaban los suplentes; este año solo los que jugaron
  < 60′ el partido oficial anterior (si no hay partido oficial en los 3 días previos, no cuenta).
- Tipo de día de 25-26: la etiqueta de la cabecera (S36 «MD-S» = MD-5); si no tiene, se deduce
  del calendario (día después de partido = MD+1; si no, MD-k hasta el siguiente partido).
- ACC + DEC: el año pasado venía en un solo número; este año se suman ACC y DEC.
"""
import datetime as dt
import json
import os
import re
import statistics as st
import subprocess
import tempfile
import unicodedata

import openpyxl

from . import config as C

PREV, ACT = "25-26", "26-27"
CARPETA_PREV = os.path.expanduser("~/Desktop/PROFESIONAL/AT BALEARES/AT BALEARES 25-26/GPS")
DIR = os.path.join(C.GPS_DIR, "Comparativa temporadas")
STORE = os.path.join(DIR, f"Temporada {PREV}.json")
HTML = os.path.join(DIR, f"Comparativa carga {PREV} vs {ACT}.html")
INFORMES = os.path.join(C.GPS_DIR, "Informes")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DIAS = ["MD+1", "MD-4", "MD-3", "MD-2", "MD-1"]
MET = ["distancia", "hmld", "hsr", "sprint", "accdec", "vmax", "pl"]
TRAMO = 5   # jornadas por tramo en la tabla de evolución


# ───────────────────────── temporada pasada (OCR) ─────────────────────────

def _cargar_store():
    if os.path.exists(STORE):
        return json.load(open(STORE))
    return {"temporada": PREV, "leidos": {}, "cabeceras": {}}


def _guardar_store(s):
    os.makedirs(DIR, exist_ok=True)
    tmp = STORE + ".tmp"
    json.dump(s, open(tmp, "w"), ensure_ascii=False, indent=0)
    os.replace(tmp, STORE)


def _tipo(key):
    if re.fullmatch(r"S\d+", key):
        return "sesion"
    if re.match(r"J\d+\b", key) or key.startswith("COPA"):
        return "partido"
    if re.match(r"PT\d+\b", key):
        return "amistoso"
    return None


def _jnum(key):
    m = re.match(r"J(\d+)\b", key)
    return int(m[1]) if m else None


def _pdfs_prev():
    out = {}
    for f in os.listdir(CARPETA_PREV):
        k = unicodedata.normalize("NFC", f[:-4])   # macOS da los nombres en NFD (Castellón)
        if f.lower().endswith(".pdf") and _tipo(k):
            out[k] = os.path.join(CARPETA_PREV, f)
    return out


def _cab(s, key, ruta):
    """Fecha y etiqueta de un PDF de 25-26 (solo cabecera, barato); se guarda en el store."""
    from . import catapult_ocr as O
    if key in s["leidos"]:
        return s["leidos"][key]
    if key not in s["cabeceras"]:
        h = O.cabecera(ruta)
        s["cabeceras"][key] = dict(head=h, fecha=O.fecha_de(h), etiqueta=O.etiqueta_de(h, key))
        _guardar_store(s)
    return s["cabeceras"][key]


def _calendario(partidos, amistosos):
    """partidos: {key: fecha} oficiales (J y COPA); amistosos: [fecha]."""
    js = sorted((_jnum(k), f) for k, f in partidos.items() if _jnum(k))
    return dict(oficiales=sorted(partidos.values()), jornadas=js, amistosos=sorted(amistosos))


def _ventana(cal, n):
    js = dict(cal["jornadas"])
    j1 = js.get(1) or min(js.values())
    if n in js:
        fin = js[n]
    elif n + 1 in js:
        fin = (dt.date.fromisoformat(js[n + 1]) - dt.timedelta(days=1)).isoformat()
    else:
        ult = max(f for j, f in cal["jornadas"] if j < n)
        fin = (dt.date.fromisoformat(ult) + dt.timedelta(days=7)).isoformat()
    pts = [f for f in cal["amistosos"] if f < j1]
    ini = (dt.date.fromisoformat(max(pts)) + dt.timedelta(days=1)).isoformat() if pts else \
        (dt.date.fromisoformat(j1) - dt.timedelta(days=7)).isoformat()
    return ini, fin


def _dia_por_calendario(fecha, cal):
    d = dt.date.fromisoformat(fecha)
    if (d - dt.timedelta(days=1)).isoformat() in cal["oficiales"]:
        return "MD+1"
    sig = [f for f in cal["oficiales"] if f > fecha]
    return f"MD-{(dt.date.fromisoformat(sig[0]) - d).days}" if sig else None


def preparar_prev(n, log=print):
    """Lee por OCR (solo lo que falta) los PDF de 25-26 de J1…Jn y sus semanas."""
    from . import catapult_ocr as O
    s = _cargar_store()
    pdfs = _pdfs_prev()
    partidos, amistosos = {}, []
    for k, r in pdfs.items():
        t = _tipo(k)
        if t == "partido" or t == "amistoso":
            f = _cab(s, k, r)["fecha"]
            if f:
                (partidos.__setitem__(k, f) if t == "partido" else amistosos.append(f))
    cal = _calendario(partidos, amistosos)
    ini, fin = _ventana(cal, n)
    sel = [k for k in pdfs if _tipo(k) == "partido" and ini <= partidos.get(k, "") <= fin]
    for k in sorted((k for k in pdfs if _tipo(k) == "sesion"), key=lambda k: int(k[1:])):
        f = _cab(s, k, pdfs[k])["fecha"]
        if f and ini <= f <= fin:
            sel.append(k)
        elif f and f > fin:
            break   # la numeración de sesiones va en orden de fecha
    nuevos = [k for k in sel if k not in s["leidos"]]
    for i, k in enumerate(nuevos, 1):
        log(f"  OCR {PREV} {i}/{len(nuevos)}: {k}")
        d = O.leer(pdfs[k])
        malos = {c: v for c, v in d["chk"].items() if v is not None and abs(v) > (6 if c == "sprint" else 1)}
        sin_ctrl = [c for c, v in d["chk"].items() if v is None]
        if sin_ctrl:
            log(f"    ⚠ {k}: fila Averages ilegible en {sin_ctrl} (sin control; las filas sí se leyeron)")
        if malos:
            log(f"    ⚠ {k}: no cuadra con la fila Averages {malos}")
        s["leidos"][k] = d
        s["cabeceras"].pop(k, None)
        _guardar_store(s)
    sesiones = []
    for k in sel:
        d = s["leidos"][k]
        t = _tipo(k)
        dia = "PARTIDO" if t == "partido" else (d.get("etiqueta") or _dia_por_calendario(d["fecha"], cal))
        rows = [dict(r) for r in d["rows"]]
        for c in MET:   # huecos del OCR: se reparte lo que falta hasta la media del PDF
            falta = [r for r in rows if c not in r]
            if falta and c in d["avg"] and c != "vmax":
                resto = d["avg"][c] * len(rows) - sum(r[c] for r in rows if c in r)
                for r in falta:
                    r[c] = max(0.0, resto / len(falta))
        sesiones.append(dict(key=k, fecha=d["fecha"], dia=dia, rows=rows, chk=d["chk"],
                             sin_pl="pl" not in d["avg"], etiqueta=d.get("etiqueta")))
    falta_s = sorted(int(k[1:]) for k in sel if _tipo(k) == "sesion")
    huecos = [i for i in range(falta_s[0], falta_s[-1]) if f"S{i}" not in pdfs] if falta_s else []
    return dict(sesiones=sesiones, cal=cal, ventana=(ini, fin), huecos=huecos)


# ───────────────────────── esta temporada (Excel) ─────────────────────────

def datos_act():
    from .pdf_catapult import dur_a_min
    from .xlsx import fecha_hoja, filas_jugadores
    out = []
    for f in sorted(os.listdir(C.MICRO_DIR)):
        m = re.fullmatch(r"Microciclo (\d+)\.xlsx", f)
        if not m:
            continue
        wb = openpyxl.load_workbook(os.path.join(C.MICRO_DIR, f), data_only=True)
        for sh in wb.sheetnames:
            if not sh.endswith("_GPS") or sh.startswith("Extra"):
                continue
            ws, k = wb[sh], sh[:-4]
            es_p = C.is_match_key(k)
            dia = k if es_p else str(ws.cell(3, 1).value or "").split("·")[-1].strip()
            filas, _ = filas_jugadores(ws)
            rows = []
            for d, r in filas.items():
                if es_p:
                    v = {c: ws.cell(r, col).value for c, col in C.MAT_COL.items()}
                    v.update(vmax=ws.cell(r, C.MAT_VMAX).value, pl=ws.cell(r, C.MAT_PL).value,
                             dur=dur_a_min(ws.cell(r, C.MAT_DUR).value))
                else:
                    v = {c: ws.cell(r, col + 1).value for c, col in C.SES_OBJ_COL.items()}
                    v.update(vmax=ws.cell(r, C.SES_VMAX).value, pl=ws.cell(r, C.SES_PL).value,
                             dur=dur_a_min(ws.cell(r, C.SES_DUR).value))
                if isinstance(v.get("distancia"), (int, float)):
                    v["accdec"] = (v.pop("acc", 0) or 0) + (v.pop("dec", 0) or 0)
                    v["dorsal"] = d
                    rows.append(v)
            if rows:
                out.append(dict(key=k, dia=dia, fecha=str(fecha_hoja(ws))[:10], micro=int(m[1]), rows=rows))
    return out


def preparar_act(n=None):
    todo = datos_act()
    partidos = {o["key"]: o["fecha"] for o in todo if re.fullmatch(r"(J|COPA)\d+", o["key"])}
    amistosos = [o["fecha"] for o in todo if o["key"].startswith("PT")]
    cal = _calendario(partidos, amistosos)
    n = n or max(j for j, _ in cal["jornadas"])
    ini, fin = _ventana(cal, n)
    ses = []
    for o in sorted(todo, key=lambda o: o["fecha"]):
        if not (ini <= o["fecha"] <= fin) or o["key"].startswith("PT"):
            continue
        o = dict(o, dia="PARTIDO" if o["key"] in partidos else o["dia"])
        if o["dia"] == "MD+1":   # solo suplentes del partido oficial anterior (≤ 3 días)
            d = dt.date.fromisoformat(o["fecha"])
            prev = [p for p in todo if p["key"] in partidos and
                    (d - dt.timedelta(days=3)).isoformat() <= p["fecha"] < o["fecha"]]
            if not prev:
                continue
            u = max(prev, key=lambda p: p["fecha"])
            tit = {r["dorsal"] for r in u["rows"] if (r.get("dur") or 0) >= 60}
            o["rows"] = [r for r in o["rows"] if r["dorsal"] not in tit]
        ses.append(o)
    return dict(sesiones=ses, cal=cal, ventana=(ini, fin), n=n)


# ───────────────────────── cálculo ─────────────────────────

def _media(rows, partido):
    if not rows:
        return None
    if partido:
        mx = max(r["distancia"] for r in rows)
        sel = [r for r in rows if r["distancia"] >= .75 * mx]
    else:
        md = st.median(r["distancia"] for r in rows)
        sel = [r for r in rows if r["distancia"] >= .6 * md]
    out = {"n": len(sel)}
    for c in MET:
        v = [r[c] for r in sel if isinstance(r.get(c), (int, float))]
        out[c] = st.mean(v) if v else None
    return out


def _jornada_de(fecha, cal):
    sig = [j for j, f in cal["jornadas"] if f >= fecha]
    return min(sig) if sig else None


def _resumen(lista):
    out = {"sesiones": len(lista), "detalle": lista}
    for c in MET:
        v = [s[c] for s in lista if s.get(c) is not None]
        out[c] = st.mean(v) if v else None
    return out


def _por_dia(datos):
    por = {}
    for o in datos["sesiones"]:
        if o["dia"] not in DIAS + ["PARTIDO"]:
            continue
        m = _media(o["rows"], o["dia"] == "PARTIDO")
        if m:
            por.setdefault(o["dia"], []).append(dict(key=o["key"], fecha=o["fecha"],
                                                    jornada=_jornada_de(o["fecha"], datos["cal"]), **m))
    return {d: _resumen(l) for d, l in por.items()}


def calcular(n=None, log=print):
    a = preparar_act(n)
    n = a["n"]
    p = preparar_prev(n, log)
    R = dict(n=n, prev=_por_dia(p), act=_por_dia(a), ventana_prev=p["ventana"], ventana_act=a["ventana"],
             huecos_prev=p["huecos"], sin_pl=[o["key"] for o in p["sesiones"] if o["sin_pl"]],
             chk_sprint=max([abs(o["chk"].get("sprint") or 0) for o in p["sesiones"]] or [0]),
             md5=[o["key"] for o in p["sesiones"] if o["dia"] not in DIAS + ["PARTIDO"]],
             deducidos=[o["key"] for o in p["sesiones"] if o["dia"] != "PARTIDO" and not o["etiqueta"]])
    # tramos de jornadas (evolución durante el año)
    R["tramos"] = []
    for t0 in range(1, n + 1, TRAMO):
        t1 = min(t0 + TRAMO - 1, n)
        fila = {"desde": t0, "hasta": t1}
        for d in DIAS + ["PARTIDO"]:
            par = []
            for src in ("prev", "act"):
                l = [s for s in R[src].get(d, {}).get("detalle", []) if s["jornada"] and t0 <= s["jornada"] <= t1]
                par.append(_resumen(l) if l else None)
            fila[d] = par
        R["tramos"].append(fila)
    return R


# ───────────────────────── página y PDF ─────────────────────────

ETIQ = [("distancia", "Distancia", "m", 0), ("hmld", "HMLD", "m", 0), ("hsr", "HSR", "m", 0),
        ("sprint", "Sprints", "", 1), ("accdec", "ACC + DEC", "", 0), ("vmax", "Vel. máx.", "km/h", 1),
        ("pl", "Player Load", "", 0)]
TITULO = {"MD+1": "MD+1 · suplentes", "MD-4": "MD-4", "MD-3": "MD-3", "MD-2": "MD-2", "MD-1": "MD-1",
          "PARTIDO": "Partido"}
NOTA = {"MD+1": f"El año pasado el GPS del MD+1 solo lo llevaban los suplentes; este año comparo también solo a "
                f"los que jugaron menos de 60′.",
        "MD-4": "Día de fuerza y espacios reducidos.", "MD-3": "Día de espacios grandes y velocidad.",
        "MD-2": "", "MD-1": "Activación previa al partido.",
        "PARTIDO": "Jugadores con al menos el 75 % de la distancia del que más corrió en cada partido "
                   "(los que jugaron casi todo)."}


def _f(v, dec=0):
    if v is None:
        return "—"
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _d(p, a):
    return (a - p) / p * 100 if p and a is not None else None


def _pct(x):
    return "—" if x is None else f"{x:+.0f} %".replace("-", "−")


def _cls(x, umbral=5):
    return "neu" if x is None or abs(x) < umbral else ("up" if x > 0 else "down")


def _semana(src, con_md1):
    dias = ["MD-4", "MD-3", "MD-2", "MD-1"] + (["MD+1"] if con_md1 else [])
    if any(d not in src for d in dias):
        return None
    return {m: sum(src[d][m] or 0 for d in dias) for m in ["distancia", "hmld", "hsr", "sprint", "accdec", "pl"]}


def _veredicto(R):
    P, A = R["prev"], R["act"]
    st_p, st_a = _semana(P, False), _semana(A, False)
    dd = _d(st_p["distancia"], st_a["distancia"]) if st_p and st_a else None
    if dd is None:
        cab = "Todavía no hay todos los tipos de día en las dos temporadas."
    elif dd <= -5:
        cab = f"Sí: el año pasado se entrenaba con más volumen (semana del titular {_pct(dd)} de distancia)."
    elif dd >= 5:
        cab = f"No: este año se entrena con más volumen (semana del titular {_pct(dd)} de distancia)."
    else:
        cab = f"Parecido: la semana del titular tiene un volumen similar ({_pct(dd)} de distancia)."
    pp = P.get("PARTIDO"), A.get("PARTIDO")
    if all(pp):
        cab += (f" Los partidos: distancia {_pct(_d(pp[0]['distancia'], pp[1]['distancia']))}, "
                f"HSR {_pct(_d(pp[0]['hsr'], pp[1]['hsr']))}.")
    deltas = {d: {m: _d(P[d][m], A[d][m]) for m in ("distancia", "hmld", "hsr", "sprint", "accdec")}
              for d in DIAS if d in P and d in A}
    peor = min(deltas, key=lambda d: deltas[d]["distancia"] or 0) if deltas else None
    mejor_v = max(deltas, key=lambda d: deltas[d]["hsr"] or -999) if deltas else None
    lis = []
    for d, x in deltas.items():
        tag = ""
        if d == peor and (x["distancia"] or 0) <= -5:
            tag = " Es donde más volumen se ha perdido."
        if d == mejor_v and (x["hsr"] or 0) >= 10:
            tag += " Es el día con más alta velocidad que el año pasado."
        lis.append(f"<li><b>{TITULO[d]}</b>: distancia {_pct(x['distancia'])}, HMLD {_pct(x['hmld'])}, "
                   f"HSR {_pct(x['hsr'])}, sprints {_pct(x['sprint'])}, ACC + DEC {_pct(x['accdec'])}.{tag}</li>")
    return f"<p><strong>{cab}</strong></p><ul>{''.join(lis)}</ul>"


def _fila(m, lab, u, dec, p, a, Pp, Pa):
    pv, av = p.get(m), a.get(m)
    d = _d(pv, av)
    cls = _cls(d)
    w = min(abs(d or 0), 60) / 60 * 50
    bar = (f'<span class="bar {cls}" style="{"left:50%" if (d or 0) >= 0 else "right:50%"};width:{w:.1f}%"></span>'
           if d is not None else "")
    pp = ""
    if Pp and Pa and m in ("distancia", "hmld", "hsr", "sprint", "accdec", "pl") and pv and av and Pp.get(m) and Pa.get(m):
        pp = f'<span class="pp">{_f(pv / Pp[m] * 100)} % · {_f(av / Pa[m] * 100)} % del partido</span>'
    return (f'<tr><th scope="row">{lab}<small>{u}</small>{pp}</th><td class="num prev">{_f(pv, dec)}</td>'
            f'<td class="num act">{_f(av, dec)}</td><td class="dl"><span class="track">{bar}<span class="mid"></span>'
            f'</span><span class="num d {cls}">{_pct(d)}</span></td></tr>')


def _tarjeta(R, dia):
    p, a = R["prev"].get(dia), R["act"].get(dia)
    if not p or not a:
        return ""
    es_p = dia == "PARTIDO"
    filas = "".join(_fila(m, l, u, dc, p, a, None if es_p else R["prev"].get("PARTIDO"),
                          None if es_p else R["act"].get("PARTIDO")) for m, l, u, dc in ETIQ)
    nota = NOTA[dia]
    if min(p["sesiones"], a["sesiones"]) < 3:
        nota += f" Poca muestra ({min(p['sesiones'], a['sesiones'])} sesiones en una de las temporadas)."
    lst = lambda x: ", ".join(s["key"] for s in sorted(x["detalle"], key=lambda s: s["fecha"]))
    return f'''<section class="card">
  <header><h3>{TITULO[dia]}</h3><p>{nota.strip()}</p></header>
  <div class="tw"><table>
   <thead><tr><th></th><th class="num prev">{PREV}</th><th class="num act">{ACT}</th><th class="dl">Diferencia</th></tr></thead>
   <tbody>{filas}</tbody></table></div>
  <p class="ses"><b>{PREV}</b> ({p["sesiones"]}): {lst(p)}<br><b>{ACT}</b> ({a["sesiones"]}): {lst(a)}</p>
</section>'''


def _tile(lab, m, p, a, u):
    d = _d(p[m], a[m])
    return (f'<div class="tile"><span class="tl">{lab}</span><span class="tv num">{_f(a[m])}<small>{u}</small></span>'
            f'<span class="tp">{PREV}: {_f(p[m])} {u}</span><span class="td num {_cls(d, 4)}">{_pct(d)}</span></div>')


def _tramos(R):
    if len(R["tramos"]) < 2:
        return ""
    cab = "".join(f"<th>{TITULO[d].split(' ·')[0]}</th>" for d in DIAS + ["PARTIDO"])
    filas = ""
    for t in R["tramos"]:
        celdas = ""
        for d in DIAS + ["PARTIDO"]:
            p, a = t[d]
            if not p or not a:
                celdas += '<td class="num neu">—</td>'
                continue
            dd, dh = _d(p["distancia"], a["distancia"]), _d(p["hsr"], a["hsr"])
            celdas += (f'<td class="num"><span class="{_cls(dd)}">{_pct(dd)}</span><br>'
                       f'<span class="{_cls(dh)} hsr">{_pct(dh)}</span></td>')
        filas += f'<tr><th scope="row">J{t["desde"]}–J{t["hasta"]}</th>{celdas}</tr>'
    return f'''<section class="sub">
  <h2>Evolución por tramos</h2>
  <p class="lead" style="margin:0">Diferencia de {ACT} frente a {PREV} en cada tramo de {TRAMO} jornadas: arriba distancia, abajo HSR. Cada sesión cuenta en la jornada que prepara.</p>
  <div class="card"><div class="tw"><table class="tramos"><thead><tr><th></th>{cab}</tr></thead><tbody>{filas}</tbody></table></div></div>
</section>'''


def pagina(R):
    P, A, n = R["prev"], R["act"], R["n"]
    st_p, st_a, ss_p, ss_a = _semana(P, False), _semana(A, False), _semana(P, True), _semana(A, True)
    T4 = [("distancia", "Distancia", "m"), ("hmld", "HMLD", "m"), ("hsr", "HSR", "m"), ("accdec", "ACC + DEC", "")]
    semana = ""
    if st_p and st_a:
        semana = f'''<section class="sub">
  <h2>La semana tipo</h2>
  <p class="lead" style="margin:0">Suma de las medias de MD-4, MD-3, MD-2 y MD-1 (titular). Con el MD+1 de suplentes, la semana de un no titular.</p>
  <span class="eyebrow">Titular · sin partido</span>
  <div class="tiles">{"".join(_tile(l, m, st_p, st_a, u) for m, l, u in T4)}</div>
  {f'<span class="eyebrow">No titular · con MD+1</span><div class="tiles">{"".join(_tile(l, m, ss_p, ss_a, u) for m, l, u in T4)}</div>' if ss_p and ss_a else ""}
  <p class="ses">Relación entrenamiento / partido del titular (distancia): {_f(st_p["distancia"] / P["PARTIDO"]["distancia"], 2)} en {PREV} y {_f(st_a["distancia"] / A["PARTIDO"]["distancia"], 2)} en {ACT}. HSR: {_f(st_p["hsr"] / P["PARTIDO"]["hsr"], 2)} y {_f(st_a["hsr"] / A["PARTIDO"]["hsr"], 2)}.</p>
</section>'''
    notas = [
        "Los PDF del año pasado no traen texto legible, así que se han leído con OCR. Cada tabla se ha comprobado "
        "contra la fila «Averages» del propio PDF: los totales cuadran al 0,0 % salvo algunos sprints de una cifra "
        f"(desvío de hasta un {_f(R['chk_sprint'], 1)} %, repartido para que la media del día sea exacta).",
        "En cada sesión cuentan los jugadores que la hicieron completa (al menos el 60 % de la distancia mediana del "
        "día), en las dos temporadas igual. Así quedan fuera readaptaciones y sesiones parciales.",
        "<b>ACC + DEC</b>: el año pasado Catapult daba «Accel&amp;Decel Efforts» en un solo número; este año se suman "
        f"ACC y DEC. En partido salen {_f(P['PARTIDO']['accdec'])} y {_f(A['PARTIDO']['accdec'])}"
        " (si son parecidos, el umbral es comparable)." if P.get("PARTIDO") and A.get("PARTIDO") else "",
        f"Player Load no aparece en algunos PDF del año pasado ({', '.join(R['sin_pl'])}): la media de esos días sale "
        "de las sesiones que sí lo tienen." if R["sin_pl"] else "",
        "No están todas las sesiones del año pasado (no hay PDF de " + _rangos(R["huecos_prev"]) +
        "), así que la comparación es por tipo de día, no por semanas completas." if R["huecos_prev"] else "",
        (f"Quedan fuera las sesiones que no son MD+1 a MD-1 ({', '.join(R['md5'])})." if R["md5"] else ""),
        (f"Sin etiqueta de día en la cabecera, deducido del calendario: {', '.join(R['deducidos'])}."
         if R["deducidos"] else ""),
        "La duración por jugador del año pasado no aparece en todos los PDF; por eso no comparo metros por minuto.",
    ]
    vp, va = R["ventana_prev"], R["ventana_act"]
    fd = lambda s: dt.date.fromisoformat(s).strftime("%d/%m/%Y")
    tarjetas = "".join(_tarjeta(R, d) for d in DIAS + ["PARTIDO"])
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carga GPS {PREV} vs {ACT}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Source+Sans+3:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap">
<style>{CSS}</style></head><body>
<main>
<header>
  <span class="eyebrow">AT Baleares · GPS · Jornadas 1 a {n}</span>
  <h1>¿Se corre más que el año pasado?</h1>
  <p class="lead">Media del equipo por sesión de cada tipo de día, temporada {PREV} frente a {ACT}, en las mismas jornadas (J1 a J{n}, Copa incluida en partidos).</p>
  <div class="key"><span class="p">{PREV}</span><span class="a">{ACT}</span></div>
</header>
<section class="verdict">{_veredicto(R)}</section>
{semana}
<section class="sub">
  <h2>Por tipo de día</h2>
  <div class="dias">{tarjetas}</div>
</section>
{_tramos(R)}
<section class="notes">
  <h2 style="color:var(--ink)">Cómo está hecho</h2>
  <ul>{"".join(f"<li>{x}</li>" for x in notas if x)}</ul>
  <p class="ses">{ACT}: del {fd(va[0])} al {fd(va[1])}. {PREV}: del {fd(vp[0])} al {fd(vp[1])}. Generado el {dt.date.today():%d/%m/%Y}.</p>
</section>
</main></body></html>'''


def _rangos(nums):
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"S{nums[i]}" if i == j else f"S{nums[i]}–S{nums[j]}")
        i = j + 1
    return ", ".join(out)


def pdf(html, destino):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html.replace("<html lang=\"es\">", "<html lang=\"es\" data-theme=\"light\">"))
    antes = os.path.getmtime(destino) if os.path.exists(destino) else 0
    r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=8000", f"--print-to-pdf={destino}", "file://" + f.name],
                       capture_output=True, text=True)
    os.unlink(f.name)
    if not os.path.exists(destino) or os.path.getmtime(destino) <= antes:
        raise RuntimeError("Chrome no generó el PDF:\n" + (r.stderr or "")[-800:])
    return destino


def generar(n=None, log=print):
    R = calcular(n, log)
    html = pagina(R)
    os.makedirs(DIR, exist_ok=True)
    open(HTML, "w", encoding="utf-8").write(html)
    destino = pdf(html, os.path.join(INFORMES, f"Comparativa carga {PREV} vs {ACT} (J1-J{R['n']}).pdf"))
    return R, HTML, destino


def tabla_texto(R):
    lin = []
    for d in DIAS + ["PARTIDO"]:
        p, a = R["prev"].get(d), R["act"].get(d)
        if not p or not a:
            continue
        lin.append(f"{d:8} ({p['sesiones']}/{a['sesiones']} ses) " + "  ".join(
            f"{m} {_pct(_d(p[m], a[m]))}" for m in ("distancia", "hmld", "hsr", "sprint", "accdec")))
    return "\n".join(lin)


CSS = """
:root { --bg:#f3f5f4; --surface:#ffffff; --ink:#15211d; --muted:#5d6b66; --line:#d9e0dd;
  --prev:#8b97a8; --act:#0f7a5c; --up:#0f7a5c; --down:#c0392b; --neu:#8a948f; --chip:#e6efeb;
  --f-display:"Barlow Condensed","Arial Narrow",system-ui,sans-serif;
  --f-body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-num:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg:#0f1513; --surface:#18201d; --ink:#e7eeeb; --muted:#9aa8a2; --line:#2a3531;
  --prev:#7d8a9c; --act:#3cc796; --up:#3cc796; --down:#ff6b5b; --neu:#7f8a85; --chip:#1f2b27; color-scheme:dark } }
:root[data-theme="dark"] { --bg:#0f1513; --surface:#18201d; --ink:#e7eeeb; --muted:#9aa8a2; --line:#2a3531;
  --prev:#7d8a9c; --act:#3cc796; --up:#3cc796; --down:#ff6b5b; --neu:#7f8a85; --chip:#1f2b27; color-scheme:dark }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 var(--f-body);
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); padding-block:20px 48px }
main { max-width:760px; margin:0 auto; display:grid; grid-template-columns:minmax(0,1fr); gap:22px }
main > *, .sub > * { min-width:0 }
h1,h2,h3 { font-family:var(--f-display); text-wrap:balance; margin:0; letter-spacing:.01em }
h1 { font-size:clamp(2rem,7vw,2.8rem); line-height:1 }
h2 { font-size:1.55rem; text-transform:uppercase; letter-spacing:.04em }
h3 { font-size:1.45rem }
.eyebrow { font:600 .78rem/1 var(--f-body); text-transform:uppercase; letter-spacing:.12em; color:var(--muted) }
.lead { color:var(--muted); margin:6px 0 0; max-width:62ch }
.key { display:flex; gap:14px; flex-wrap:wrap; font-size:.85rem; color:var(--muted); margin-top:10px }
.key span::before { content:""; display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; background:currentColor }
.key .p { color:var(--prev) } .key .a { color:var(--act) }
.verdict { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:18px; display:grid; gap:10px }
.verdict p { margin:0 } .verdict strong { font-weight:700 }
.verdict ul { margin:0; padding-left:1.1em; display:grid; gap:6px }
.tiles { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px }
@media (max-width:620px) { .tiles { grid-template-columns:repeat(2,minmax(0,1fr)) } }
.tile { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:12px; display:grid; gap:2px; min-width:0 }
.tl { font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); font-weight:600 }
.tv { font-family:var(--f-display); font-size:1.9rem; line-height:1.05; color:var(--act) }
.tv small { font-size:.9rem; margin-left:3px; color:var(--muted) }
.tp { font-size:.82rem; color:var(--muted) }
.td { font-size:.9rem }
.num { font-family:var(--f-num); font-variant-numeric:tabular-nums }
.up { color:var(--up) } .down { color:var(--down) } .neu { color:var(--neu) }
.sub { display:grid; gap:8px; grid-template-columns:minmax(0,1fr) }
.card { background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:16px; display:grid; gap:10px; min-width:0 }
.card header p { margin:2px 0 0; color:var(--muted); font-size:.92rem }
.tw { overflow-x:auto }
table { width:100%; border-collapse:collapse; font-size:.92rem }
th, td { padding:7px 6px; border-bottom:1px solid var(--line); text-align:left; vertical-align:middle }
tbody tr:last-child th, tbody tr:last-child td { border-bottom:0 }
thead th { font:600 .72rem/1 var(--f-body); text-transform:uppercase; letter-spacing:.08em; color:var(--muted) }
tbody th { font-weight:600; white-space:nowrap }
tbody th small { font-weight:400; color:var(--muted); margin-left:4px; font-size:.75rem }
.pp { display:block; font-weight:400; font-size:.72rem; color:var(--muted); white-space:normal }
td.num, th.num { text-align:right; white-space:nowrap }
td.prev { color:var(--prev) } td.act { color:var(--act); font-weight:600 }
th.prev { color:var(--prev) } th.act { color:var(--act) }
td.dl { white-space:nowrap }
.tramos td, .tramos thead th { text-align:center; font-size:.82rem }
.tramos .hsr { font-size:.75rem }
@media (max-width:480px) { .track { width:40px } table { font-size:.86rem } th, td { padding:7px 4px } }
.track { position:relative; display:inline-block; width:64px; height:8px; vertical-align:middle; background:var(--chip); border-radius:4px; margin-right:8px }
.mid { position:absolute; left:50%; top:-2px; bottom:-2px; width:1px; background:var(--muted) }
.bar { position:absolute; top:0; bottom:0; border-radius:4px }
.bar.up { background:var(--up) } .bar.down { background:var(--down) } .bar.neu { background:var(--neu) }
.d { display:inline-block; min-width:52px; text-align:right; font-size:.88rem }
.ses { margin:0; font-size:.78rem; color:var(--muted) }
.notes { font-size:.9rem; color:var(--muted); display:grid; gap:8px }
.notes ul { margin:0; padding-left:1.1em; display:grid; gap:6px }
@page { size:A4; margin:12mm }
.dias { display:grid; gap:8px; grid-template-columns:minmax(0,1fr) }
@media print {
  body { padding:0; background:#fff; font-size:11px; -webkit-print-color-adjust:exact; print-color-adjust:exact }
  main, .sub { display:block; max-width:none }
  main > section, main > header { margin-bottom:14px }
  .sub > * { margin-bottom:6px }
  h1 { font-size:2.2rem } h2 { font-size:1.3rem } h3 { font-size:1.15rem }
  .dias { display:block; font-size:0 }
  .dias .card { display:inline-block; width:calc(50% - 5px); vertical-align:top; margin:0 0 10px; font-size:11px; box-sizing:border-box }
  .dias .card:nth-child(odd) { margin-right:10px }
  .card { padding:10px; gap:6px }
  .card > * + * { margin-top:6px }
  th, td { padding:4px 4px } table { font-size:.88rem }
  .track { width:44px }
  .tv { font-size:1.6rem }
  .card, .tile, .verdict, .tiles, .notes li { break-inside:avoid }
  h2 { break-after:avoid }
}
"""
