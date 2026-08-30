#!/usr/bin/env python3
"""Genera data.js con datos de ejemplo (3 microciclos) para la app de carga GPS.
Vuelve a ejecutarlo con `python3 gen_data.py` cuando quieras regenerar el ejemplo.
Los datos reales sustituyen a window.GPS_DATA_ALL directamente en data.js."""
import json, random, math

random.seed(7)

# ----------------------------------------------------------------------------
# Plantilla
# ----------------------------------------------------------------------------
ROSTER = [
    # dorsal, "Apellido, I.", grupo, posicion
    (1,  "Herrero, D.",  "P", "GK"),
    (13, "Nkodia, P.",   "P", "GK"),
    (25, "Salas, J.",    "P", "GK"),
    (2,  "Ferrer, A.",   "D", "DF"),
    (3,  "Quintana, R.", "D", "DF"),
    (4,  "Baptista, L.", "D", "DF"),
    (5,  "Ndiaye, M.",   "D", "DF"),
    (15, "Cabral, T.",   "D", "DF"),
    (17, "Otero, G.",    "D", "DF"),
    (23, "Villalba, S.", "D", "DF"),
    (6,  "Saez, I.",     "D", "MF"),
    (8,  "Moreno, C.",   "D", "MF"),
    (10, "Prieto, A.",   "D", "MF"),
    (14, "Duran, K.",    "D", "MF"),
    (16, "Escudero, P.", "D", "MF"),
    (20, "Almeida, R.",  "D", "MF"),
    (21, "Vega, H.",     "D", "MF"),
    (7,  "Rincon, D.",   "D", "FW"),
    (9,  "Bakary, O.",   "D", "FW"),
    (11, "Sola, E.",     "D", "FW"),
    (19, "Kovac, M.",    "D", "FW"),
    (22, "Ferreira, N.", "D", "FW"),
]

BASE = {  # REF_PARTIDO por posicion, estimado a 95'
    "GK": dict(distancia=5400, hmld=380,  hsr=45,  sprint=2,  acc=14, dec=15),
    "DF": dict(distancia=9850, hmld=1060, hsr=470, sprint=17, acc=41, dec=43),
    "MF": dict(distancia=11250,hmld=1360, hsr=560, sprint=20, acc=52, dec=54),
    "FW": dict(distancia=10450,hmld=1500, hsr=820, sprint=32, acc=47, dec=46),
}
METRICS = ["distancia", "hmld", "hsr", "sprint", "acc", "dec"]

# ----------------------------------------------------------------------------
# Coeficientes por Tipo de microciclo y dia
# ----------------------------------------------------------------------------
COEF = {
    "A": {
        "+1":   dict(distancia=.40, hmld=.36, hsr=.16, sprint=.12, acc=.36, dec=.36),
        "MD-4": dict(distancia=.80, hmld=.78, hsr=.44, sprint=.36, acc=.80, dec=.80),
        "MD-3": dict(distancia=1.15,hmld=1.12,hsr=1.02,sprint=.92, acc=1.12,dec=1.12),
        "MD-2": dict(distancia=.72, hmld=.66, hsr=.74, sprint=.72, acc=.78, dec=.78),
        "MD-1": dict(distancia=.48, hmld=.40, hsr=.26, sprint=.20, acc=.46, dec=.46),
    },
    "B": {
        "+1":   dict(distancia=.38, hmld=.34, hsr=.14, sprint=.10, acc=.34, dec=.34),
        "MD-4": dict(distancia=.70, hmld=.66, hsr=.52, sprint=.40, acc=.72, dec=.72),
        "MD-3": dict(distancia=1.05,hmld=1.02,hsr=.95, sprint=.85, acc=1.05,dec=1.05),
        "MD-2": dict(distancia=.78, hmld=.72, hsr=.70, sprint=.68, acc=.82, dec=.82),
        "MD-1": dict(distancia=.52, hmld=.44, hsr=.30, sprint=.22, acc=.50, dec=.50),
    },
}

# ----------------------------------------------------------------------------
# REF_PARTIDO por jugador
# ----------------------------------------------------------------------------
def jitter(v, pct):
    return v * (1 + random.uniform(-pct, pct))

ref_players = []
REF = {}          # dorsal -> dict de metricas
VELMAX_PERS = {}  # dorsal -> velocidad maxima personal
for dorsal, nombre, grupo, pos in ROSTER:
    b = BASE[pos]
    r = {m: max(0, round(jitter(b[m], .07))) for m in METRICS}
    partidos = random.randint(5, 9) if pos == "GK" else random.randint(3, 8)
    REF[dorsal] = r
    VELMAX_PERS[dorsal] = round(
        (26.0 if pos == "GK" else 32.0 if pos in ("FW",) else 31.0) + random.uniform(-1.5, 2.2), 1)
    ref_players.append(dict(dorsal=dorsal, jugador=nombre, grupo=grupo,
                            distancia=r["distancia"], hmld=r["hmld"], hsr=r["hsr"],
                            sprint=r["sprint"], acc=r["acc"], dec=r["dec"],
                            velMax=VELMAX_PERS[dorsal], partidos=partidos))

# ----------------------------------------------------------------------------
# Perfil de cumplimiento por jugador (para que el semaforo tenga variedad)
# ----------------------------------------------------------------------------
PROFILE = {}  # dorsal -> (media_factor, sigma)
for dorsal, nombre, grupo, pos in ROSTER:
    PROFILE[dorsal] = (random.gauss(1.0, 0.045), random.uniform(0.05, 0.09))
# forzamos algunos casos de demostracion
PROFILE[6]  = (0.86, 0.05)   # Saez: corto de forma cronica
PROFILE[17] = (0.88, 0.05)   # Otero: corto
PROFILE[10] = (1.14, 0.06)   # Prieto: se pasa
PROFILE[7]  = (1.17, 0.07)   # Rincon: se pasa mucho en dias de alta intensidad
PROFILE[20] = (1.32, 0.06)   # Almeida: vuelve de ausencia y fuerza para ponerse a tono

def fmt_dur(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"

DUR_BASE = {"+1": 35*60, "MD-4": 66*60, "MD-3": 74*60, "MD-2": 58*60, "MD-1": 42*60, "Partido": 95*60}

def player_load(real):
    d = real.get("distancia") or 0
    h = real.get("hsr") or 0
    a = (real.get("acc") or 0) + (real.get("dec") or 0)
    return round(d/22 + h/5.5 + a*1.4)

# ----------------------------------------------------------------------------
# Construccion de una sesion
# ----------------------------------------------------------------------------
def build_session(tipo, dia, date, especiales, completed=True):
    """especiales: dict dorsal -> 'rehab' | 'na' | 'parcial'"""
    coef = COEF[tipo][dia] if dia != "Partido" else {m: 1.0 for m in METRICS}
    players = []
    acc_avg = {m: [] for m in METRICS}
    velmax_avg, pl_avg = [], []
    for dorsal, nombre, grupo, pos in ROSTER:
        estado = especiales.get(dorsal)
        obj = {m: max(1, round(REF[dorsal][m] * coef[m])) for m in METRICS}
        row = dict(dorsal=dorsal, jugador=nombre, grupo=grupo)

        if estado == "na" or not completed:
            for m in METRICS:
                row[m] = dict(obj=(None if estado == "na" else obj[m]), real=None, dif=None)
            row.update(velMax=None, playerLoad=None, duracion=None)
            if estado:
                row["estado"] = estado
            players.append(row)
            continue

        mu, sg = PROFILE[dorsal]
        if dia in ("MD-3", "Partido"):
            mu += 0.02
        real = {}
        for m in METRICS:
            f = max(0.62, min(1.4, random.gauss(mu, sg)))
            real[m] = max(0, round(obj[m] * f))

        if estado == "rehab":
            # informativo: sin objetivo, valores mas bajos (trabajo individual)
            for m in METRICS:
                real[m] = round(real[m] * random.uniform(0.45, 0.7))
                row[m] = dict(obj=None, real=real[m], dif=None)
            dur = round(DUR_BASE[dia] * random.uniform(0.55, 0.8))
            row.update(velMax=round(VELMAX_PERS[dorsal] * random.uniform(0.7, 0.82), 1),
                       playerLoad=player_load(real), duracion=fmt_dur(dur), estado="rehab")
            players.append(row)
            continue

        parcial = estado == "parcial"
        if parcial:
            k = random.uniform(0.55, 0.72)
            for m in METRICS:
                real[m] = round(real[m] * k)

        for m in METRICS:
            row[m] = dict(obj=obj[m], real=real[m], dif=real[m] - obj[m])
            acc_avg[m].append(real[m])

        dur_f = random.uniform(0.95, 1.06) * (random.uniform(0.55, 0.72) if parcial else 1)
        vf = 0.98 if dia in ("MD-3", "MD-4", "Partido") else random.uniform(0.78, 0.9)
        vmax = round(VELMAX_PERS[dorsal] * vf * random.uniform(0.97, 1.03), 1)
        pl = player_load(real)
        row.update(velMax=vmax, playerLoad=pl, duracion=fmt_dur(round(DUR_BASE[dia] * dur_f)))
        if parcial:
            row["estado"] = "parcial"
        players.append(row)
        if grupo == "D":
            velmax_avg.append(vmax)
            pl_avg.append(pl)

    def avg(xs):
        return round(sum(xs) / len(xs)) if xs else None

    team = {m: None for m in METRICS}
    if completed:
        team = {}
        for m in METRICS:
            vals = acc_avg[m]
            o = [REF[d]["distancia"] for d in []]  # placeholder
            # objetivo medio del equipo: media de objetivos de jugadores de campo comparables
            objs = [max(1, round(REF[dorsal][m] * coef[m]))
                    for dorsal, nombre, grupo, pos in ROSTER
                    if grupo == "D" and especiales.get(dorsal) not in ("na", "rehab")]
            oavg = round(sum(objs) / len(objs)) if objs else None
            ravg = avg(vals)
            team[m] = dict(obj=oavg, real=ravg,
                           dif=(None if (oavg is None or ravg is None) else ravg - oavg))
        team["velMax"] = avg(velmax_avg)
        team["playerLoad"] = avg(pl_avg)

    return dict(date=date, players=players, teamAvg=team)

# ----------------------------------------------------------------------------
# Microciclos
# ----------------------------------------------------------------------------
LEYENDA = ("LEYENDA — Semaforo por metrica: AZUL corto (real < -10% del objetivo) · "
           "VERDE cumplido (dentro de +-10%) · NARANJA pasado (+10% a +20%) · ROJO muy pasado (>+20%). "
           "Objetivo = REF_PARTIDO individual x coeficiente del dia segun el Tipo de microciclo. "
           "La media del equipo se calcula solo con jugadores de campo comparables "
           "(excluye REHAB, N/A y porteros).")

def micro(key, tipo, meta, sess_defs, especiales_por_sesion, pending=()):
    sessions = {}
    all_sess_keys = [s[0] for s in sess_defs if not s[0].startswith("PT")]
    for skey, dia, date in sess_defs:
        esp = especiales_por_sesion.get(skey, {})
        completed = skey not in pending
        s = build_session(tipo, dia, date, esp, completed=completed)
        notas = [f"{skey} · {dia} · {date}.", LEYENDA]
        # notas de jugadores segun estado
        for dorsal, est in esp.items():
            nom = next(n for d, n, g, p in ROSTER if d == dorsal)
            if est == "rehab":
                notas.append(f"{nom}: trabajo individual (REHAB). Dato informativo, no cuenta para la media ni contra objetivo.")
            elif est == "na":
                notas.append(f"{nom}: no participa en la sesion (N/A).")
            elif est == "parcial":
                notas.append(f"{nom}: participacion parcial, duracion reducida; se compara con normalidad.")
        if not completed:
            notas.append("Sesion prevista, aun sin datos: se muestran solo los objetivos.")
        s["nota"] = " ".join(notas)
        if skey.startswith("PT"):
            pass
        sessions[skey] = s

    # separa el partido (PTx)
    ptkey = next((s[0] for s in sess_defs if s[0].startswith("PT")), None)
    ptdata = sessions.pop(ptkey) if ptkey else None

    # ------- acumulados -------
    def accumulate(include_match, nota):
        keys = [k for k, _, _ in sess_defs
                if not k.startswith("PT") or (include_match and k == ptkey)]
        aplayers = []
        team_acc = {m: {"obj": [], "real": []} for m in METRICS}
        for dorsal, nombre, grupo, pos in ROSTER:
            pr = dict(dorsal=dorsal, jugador=nombre, grupo=grupo)
            for m in METRICS:
                tot_obj = tot_real = 0
                has_real = False
                for skey in keys:
                    sd = ptdata if skey == ptkey else sessions.get(skey)
                    if sd is None:
                        continue
                    cell = next(r for r in sd["players"] if r["dorsal"] == dorsal).get(m)
                    if isinstance(cell, dict):
                        if cell.get("obj") is not None:
                            tot_obj += cell["obj"]
                        if cell.get("real") is not None:
                            tot_real += cell["real"]
                            has_real = True
                pr[m] = dict(obj=tot_obj or None,
                             real=(tot_real if has_real else None),
                             dif=(tot_real - tot_obj) if has_real else None)
                if grupo == "D" and tot_obj:
                    team_acc[m]["obj"].append(tot_obj)
                    if has_real:
                        team_acc[m]["real"].append(tot_real)
            aplayers.append(pr)
        team = {}
        for m in METRICS:
            o, r = team_acc[m]["obj"], team_acc[m]["real"]
            oavg = round(sum(o) / len(o)) if o else None
            ravg = round(sum(r) / len(r)) if r else None
            team[m] = dict(obj=oavg, real=ravg,
                           dif=(None if (oavg is None or ravg is None) else ravg - oavg))
        return dict(players=aplayers, teamAvg=team, nota=nota + " " + LEYENDA)

    cargas = accumulate(False,
        "Objetivo acumulado de las sesiones de entrenamiento de la semana (sin el partido). "
        "La diferencia negativa indica carga que aun falta por completar.")
    cargas_semana = accumulate(True,
        "Objetivo acumulado de toda la semana: sesiones de entrenamiento + partido.")

    return dict(meta=meta, sessions=sessions, **({ptkey: ptdata} if ptkey else {}),
                cargasObjetivo=cargas, cargasSemana=cargas_semana), sessions, ptdata, ptkey


from datetime import date as _date, timedelta as _td

def _d(iso):
    return _date.fromisoformat(iso)

# Se rellenan tras construir los microciclos:
SESS_PL = {}      # iso_date -> {dorsal: playerLoad}  (PL real de sesion)
SESS_LABEL = {}   # iso_date -> "S27"
FIRST_SESSION = None

def register_sessions(*micros):
    """micros: lista de (sessions_dict, ptdata|None, ptkey|None)"""
    global FIRST_SESSION
    all_dates = []
    for sessions, ptdata, ptkey in micros:
        rows = list(sessions.items())
        if ptkey:
            rows.append((ptkey, ptdata))
        for skey, s in rows:
            SESS_LABEL[s["date"]] = skey
            all_dates.append(s["date"])
            for r in s["players"]:
                pl = r.get("playerLoad")
                if pl is not None:
                    SESS_PL.setdefault(s["date"], {})[r["dorsal"]] = pl
    FIRST_SESSION = min(_d(x) for x in all_dates)

_field_pl_ref = None
def _pl_scale(dorsal):
    """Escala de carga por jugador (proxy: distancia REF). Porteros ~0.5."""
    global _field_pl_ref
    if _field_pl_ref is None:
        fv = [REF[dd]["distancia"] for dd, _, g, _ in ROSTER if g == "D"]
        _field_pl_ref = sum(fv) / len(fv)
    return REF[dorsal]["distancia"] / _field_pl_ref

def _baseline_pl(dd, dorsal):
    """Trabajo de base de pretemporada, antes del primer microciclo modelado."""
    wd = dd.weekday()          # 0 = lunes ... 6 = domingo
    if wd == 6:
        base = random.randint(0, 60)
    elif wd == 5:
        base = random.randint(200, 300)
    else:
        base = random.randint(360, 500)
    return round(base * _pl_scale(dorsal))

def daily_series(calc_iso, dorsal, expose=28, hist=27, zero_dates=None):
    """Serie diaria de Player Load de los ultimos `expose` dias hasta calc_iso,
    con medias moviles de 7 dias (aguda), 28 dias (cronica) y ACWR de cada dia.
    zero_dates: fechas en las que el PL de sesion NO cuenta (p.ej. rehab en piscina)."""
    zero_dates = zero_dates or set()
    asof = _d(calc_iso)
    start = asof - _td(days=expose - 1 + hist)
    pl = {}
    dd = start
    while dd <= asof:
        di = dd.isoformat()
        if di in zero_dates:
            pl[di] = 0
        elif di in SESS_PL and dorsal in SESS_PL[di]:
            pl[di] = SESS_PL[di][dorsal]
        elif di in SESS_PL:
            pl[di] = 0                         # el equipo entreno; este jugador descanso / ausente
        elif dd < FIRST_SESSION:
            pl[di] = _baseline_pl(dd, dorsal)  # trabajo de base previo a los microciclos
        else:
            pl[di] = 0                         # dia de descanso dentro de temporada
        dd += _td(days=1)

    dias, plv, agv, crv, acv, ses = [], [], [], [], [], []
    dd = asof - _td(days=expose - 1)
    while dd <= asof:
        wk = sum(pl[(dd - _td(days=k)).isoformat()] for k in range(7))
        mo = sum(pl[(dd - _td(days=k)).isoformat()] for k in range(28))
        ag, cr = round(wk / 7), round(mo / 28)
        di = dd.isoformat()
        dias.append(di); plv.append(pl[di]); agv.append(ag); crv.append(cr)
        acv.append(round(ag / cr, 2) if cr else 0.0)
        ses.append(SESS_LABEL.get(di, "") if pl[di] else "")
        dd += _td(days=1)
    return dict(dias=dias, pl=plv, aguda=agv, cronica=crv, acwr=acv, ses=ses)

def build_carga_ac(sessions, calc_iso, calc_label, zero_by_dorsal=None, avisos_extra=None):
    """ACWR por medias moviles diarias (7 d / 28 d) evaluadas en calc_iso.
    sessions: dict de sesiones completas del microciclo (para las columnas plSxx del panel de entrenador)."""
    zero_by_dorsal = zero_by_dorsal or {}
    avisos_extra = avisos_extra or {}
    session_keys = list(sessions.keys())
    players, serie_dias = [], None
    acwr_avg, ag_avg, cr_avg = [], [], []

    for dorsal, nombre, grupo, pos in ROSTER:
        pr = dict(dorsal=dorsal, jugador=nombre, grupo=grupo)
        for skey in session_keys:
            row = next(r for r in sessions[skey]["players"] if r["dorsal"] == dorsal)
            pr["pl" + skey] = None if dorsal in zero_by_dorsal else row.get("playerLoad")

        s = daily_series(calc_iso, dorsal, zero_dates=zero_by_dorsal.get(dorsal))
        serie_dias = s["dias"]
        aguda, cronica = s["aguda"][-1], s["cronica"][-1]
        acwr = s["acwr"][-1]
        pr.update(acwr=acwr,
                  cargaAguda=aguda or None,
                  cargaCronica=cronica or None,
                  serie=dict(pl=s["pl"], aguda=s["aguda"], cronica=s["cronica"], acwr=s["acwr"], ses=s["ses"]))
        players.append(pr)
        if grupo == "D" and cronica and acwr:
            acwr_avg.append(acwr); ag_avg.append(aguda); cr_avg.append(cronica)

    team = dict(
        acwr=round(sum(acwr_avg) / len(acwr_avg), 2) if acwr_avg else None,
        cargaAguda=round(sum(ag_avg) / len(ag_avg)) if ag_avg else None,
        cargaCronica=round(sum(cr_avg) / len(cr_avg)) if cr_avg else None)

    avisos = []
    for pr in players:
        if pr["dorsal"] in avisos_extra:
            avisos.append(avisos_extra[pr["dorsal"]])
        elif pr["acwr"] == 0.0:
            avisos.append(f"{pr['jugador']}: ACWR 0,00 — sin Player Load acumulado en 7 dias. Revisar reintroduccion progresiva.")
        elif pr["acwr"] and pr["acwr"] > 1.30:
            avisos.append(f"{pr['jugador']}: ACWR {str(pr['acwr']).replace('.',',')} — por encima de 1,30, zona de riesgo. Vigilar volumen.")
        elif pr["acwr"] and pr["acwr"] < 0.80:
            avisos.append(f"{pr['jugador']}: ACWR {str(pr['acwr']).replace('.',',')} — por debajo de 0,80, infracarga.")
    nota = (f"Calculo a {calc_label}. Carga aguda = media de Player Load de los ultimos 7 dias "
            f"(incluye dias de descanso). Carga cronica = media de los ultimos 28 dias. "
            f"ACWR = aguda / cronica, calculado cada dia. Zona optima 0,80-1,30. "
            + (" ".join(avisos) if avisos else "Sin avisos individuales."))
    return dict(players=players, teamAvg=team, nota=nota, serieDias=serie_dias)

# ============================================================================
# M5 (cerrado, Tipo A)
# ============================================================================
m5_defs = [("S16", "+1", "2026-08-10"), ("S17", "MD-4", "2026-08-11"),
           ("S18", "MD-3", "2026-08-12"), ("S19", "MD-2", "2026-08-13"),
           ("S20", "MD-1", "2026-08-14"), ("PT7", "Partido", "2026-08-15")]
m5_meta = dict(titulo="MICROCICLO 5 · TIPO A", semana="PRETEMP S5 (10-16 AGO)",
               temporada="2026-27", calculoFecha="16/08 (tras PT7)")
# Almeida (20) llega tarde a la pretemporada: se pierde la 2a mitad de M5
m5_esp = {"S19": {20: "na"}, "S20": {20: "na"}, "PT7": {20: "na"}}
m5, m5_sessions, m5_pt, _ = micro("M5", "A", m5_meta, m5_defs, m5_esp, pending=())

# ============================================================================
# M6 (cerrado, Tipo A)
# ============================================================================
m6_defs = [("S21", "+1", "2026-08-17"), ("S22", "MD-4", "2026-08-18"),
           ("S23", "MD-3", "2026-08-19"), ("S24", "MD-2", "2026-08-20"),
           ("S25", "MD-1", "2026-08-21"), ("PT8", "Partido", "2026-08-22")]
m6_meta = dict(titulo="MICROCICLO 6 · TIPO A", semana="PRETEMP S6 (17-23 AGO)",
               temporada="2026-27", calculoFecha="23/08 (tras PT8)")
m6_esp = {
    "S21": {23: "rehab", 20: "na"},
    "S22": {23: "rehab", 20: "na"},
    "S23": {23: "rehab", 20: "na"},
    "S24": {23: "rehab", 20: "na"},
    "S25": {23: "rehab", 20: "na"},
    "PT8": {23: "na", 20: "na"},
}
m6, m6_sessions, m6_pt, _ = micro("M6", "A", m6_meta, m6_defs, m6_esp, pending=())

# ============================================================================
# M7 (ACTIVO, Tipo B) — S26-S29 hechas, S30 y PT9 previstas
# ============================================================================
m7_defs = [("S26", "+1", "2026-08-24"), ("S27", "MD-4", "2026-08-25"),
           ("S28", "MD-3", "2026-08-26"), ("S29", "MD-2", "2026-08-27"),
           ("S30", "MD-1", "2026-08-28"), ("PT9", "Partido", "2026-08-29")]
m7_meta = dict(titulo="MICROCICLO 7 · TIPO B", semana="PRETEMP S7 (24-30 AGO)",
               temporada="2026-27", calculoFecha="27/08 (S29)", calculoISO="2026-08-27")
m7_esp = {
    "S26": {19: "na", 23: "rehab"},
    "S27": {3: "rehab", 23: "rehab"},
    "S28": {3: "rehab", 11: "parcial", 23: "rehab"},
    "S29": {19: "na", 23: "rehab"},
}
m7, m7_sessions, m7_pt, _ = micro("M7", "B", m7_meta, m7_defs, m7_esp, pending=("S30", "PT9"))

# ---- carga aguda-cronica (medias moviles diarias 7 d / 28 d) ----
register_sessions((m5_sessions, m5_pt, "PT7"),
                  (m6_sessions, m6_pt, "PT8"),
                  (m7_sessions, m7_pt, "PT9"))

# Villalba (23): rehab desde M6; su trabajo individual no cuenta como carga GPS.
villa_zero = set()
for defs, esp in ((m5_defs, m5_esp), (m6_defs, m6_esp), (m7_defs, m7_esp)):
    for skey, dia, dt in defs:
        if esp.get(skey, {}).get(23) in ("rehab", "na"):
            villa_zero.add(dt)

m5["cargaAC"] = build_carga_ac(m5_sessions, "2026-08-16", "16/08 (tras PT7)",
                               zero_by_dorsal={23: villa_zero})
m6["cargaAC"] = build_carga_ac(m6_sessions, "2026-08-23", "23/08 (tras PT8)",
                               zero_by_dorsal={23: villa_zero})
m7_ac_sessions = {k: m7_sessions[k] for k in ("S26", "S27", "S28", "S29")}
m7["cargaAC"] = build_carga_ac(
    m7_ac_sessions, "2026-08-27", "27/08 (S29)",
    zero_by_dorsal={23: villa_zero},
    avisos_extra={23: ("Villalba, S.: ACWR 0,00 — sin Player Load acumulado en 7 dias "
                       "(solo trabajo individual). Revisar reintroduccion progresiva antes de exponer a MD-3.")})

# ============================================================================
# media de REF_PARTIDO del equipo (solo jugadores de campo)
_ref_field = [p for p in ref_players if p["grupo"] == "D"]
_ref_metrics = METRICS + ["velMax"]
ref_team_avg = {}
for _m in _ref_metrics:
    _vals = [p[_m] for p in _ref_field]
    ref_team_avg[_m] = round(sum(_vals) / len(_vals), 1 if _m == "velMax" else 0)
    if _m != "velMax":
        ref_team_avg[_m] = int(ref_team_avg[_m])

DATA = {
    "refPartido": {
        "nota": ("REF_PARTIDO individual = media de todos los partidos validos del jugador, "
                 "cada uno estimado a 95' con formula de fatiga. Es la base de todos los objetivos. "
                 "Los objetivos son individuales, nunca de equipo. "
                 "La media del equipo se calcula solo con jugadores de campo."),
        "players": ref_players,
        "teamAvg": ref_team_avg,
    },
    "coeficientes": {
        "nota": "Coeficiente de carga por Tipo de microciclo y dia. Objetivo del dia = REF_PARTIDO x coeficiente.",
        "tipos": COEF,
    },
    "M7": m7,
    "M6": m6,
    "M5": m5,
}

with open("data.js", "w", encoding="utf-8") as f:
    f.write("/* Datos de la app de carga GPS. Generado por gen_data.py — datos de EJEMPLO. */\n")
    f.write("/* Estructura: window.GPS_DATA_ALL = { refPartido, coeficientes, M7, M6, M5 }. */\n")
    f.write("window.GPS_DATA_ALL = ")
    json.dump(DATA, f, ensure_ascii=False, indent=1)
    f.write(";\n")

print("data.js generado.")
print("Microciclos:", [k for k in DATA if k.startswith("M")])
print("M7 sesiones:", list(m7["sessions"].keys()), "+ PT9")
