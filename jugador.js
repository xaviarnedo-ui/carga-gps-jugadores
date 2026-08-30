/* =========================================================================
   Carga GPS — VISTA JUGADOR (solo sus datos + media del equipo)
   ========================================================================= */
(function () {
  "use strict";

  var DATA = window.GPS_DATA_ALL;
  var view = document.getElementById("view");
  if (!DATA) { view.innerHTML = "<p class='muted'>No se encuentra data.js</p>"; return; }

  var MICROS = (DATA.microciclos && DATA.microciclos.length)
    ? DATA.microciclos.slice()
    : Object.keys(DATA).filter(function (k) { return /^M\d+$/.test(k); })
        .sort(function (a, b) { return (+b.slice(1)) - (+a.slice(1)); });

  var METRICS = [
    { key: "distancia", label: "Distancia", short: "DIST", unit: "m" },
    { key: "hmld", label: "HMLD", short: "HMLD", unit: "m" },
    { key: "hsr", label: "HSR", short: "HSR", unit: "m" },
    { key: "sprint", label: "Sprints", short: "SPR", unit: "nº" },
    { key: "acc", label: "ACC", short: "ACC", unit: "nº" },
    { key: "dec", label: "DEC", short: "DEC", unit: "nº" }
  ];
  var RADAR = METRICS.concat([{ key: "velMax", label: "Vel. máx", short: "VMÁX", unit: "km/h", dec: 1 }]);

  /* ----------------------------- utilidades ----------------------------- */
  var nf = new Intl.NumberFormat("es-ES");
  function fmt(v) { return (v === null || v === undefined) ? "—" : nf.format(Math.round(v)); }
  function fmtDec(v, d) {
    if (v === null || v === undefined) return "—";
    return v.toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function semaphore(real, obj) {
    if (real == null || obj == null || obj === 0) return null;
    var p = (real - obj) / obj;
    if (p < -0.10) return "sem-azul";
    if (p <= 0.10) return "sem-verde";
    if (p <= 0.20) return "sem-naranja";
    return "sem-rojo";
  }
  function acwrClass(v) {
    if (v == null) return "";
    if (v === 0) return "zero";
    if (v < 0.80) return "low";
    if (v <= 1.30) return "ok";
    if (v <= 1.50) return "warn";
    return "high";
  }
  function sessionKeys(m) { return (m.orden || []).map(function (o) { return o.key; }); }
  function getSession(m, k) { return (m.sesiones && m.sesiones[k]) || (m.partidos && m.partidos[k]); }
  function isMatch(m, k) { return !!(m.partidos && m.partidos[k]); }
  function sessionRole(s) { return (s && s.role) || "—"; }
  function roleShort(r) { return r || "—"; }
  function chartTag(m, k) {
    if (isMatch(m, k)) return k;
    var r = (((m.sesiones && m.sesiones[k]) || {}).role || "").trim();
    if (/^md\s*-?\s*\d/i.test(r)) return r.replace(/\s+/g, "").toUpperCase();
    if (/\+\s*1/.test(r)) return "+1";
    if (/^mixto$/i.test(r)) return "MIX";
    return k;
  }
  function isCompleted(s) { return !!(s && s.teamAvg && s.teamAvg.distancia && s.teamAvg.distancia.real != null); }
  function lastCompletedKey(m) { var ks = sessionKeys(m), last = null; ks.forEach(function (k) { if (isCompleted(getSession(m, k))) last = k; }); return last || ks[0]; }
  function pct(a, b) { return (a == null || b == null || !b) ? null : Math.round((a - b) / b * 100); }
  function signed(p) { return p == null ? "—" : (p > 0 ? "+" : "") + p + "%"; }
  function iconWarn() { return '<svg viewBox="0 0 24 24" width="16" height="16"><path d="M12 3 2 20h20Zm0 6v5m0 3v.5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg>'; }
  function iconOk() { return '<svg viewBox="0 0 24 24" width="16" height="16"><path d="m4 12 5 5L20 6" stroke="currentColor" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'; }

  function trendBars(pairs) {
    var vals = pairs.map(function (p) { return p.value; }).filter(function (v) { return v != null; });
    if (!vals.length) return '<div class="muted" style="padding:8px 0">Sin Player Load registrado en el microciclo.</div>';
    var max = Math.max.apply(null, vals);
    return '<div class="trend-bars">' + pairs.map(function (p) {
      if (p.value == null) return '<div class="b" style="height:3px;background:var(--line)"><em>' + esc(p.label) + '</em></div>';
      var h = Math.max(6, Math.round((p.value / max) * 92));
      return '<div class="b" style="height:' + h + 'px"><span>' + fmt(p.value) + '</span><em>' + esc(p.label) + '</em></div>';
    }).join("") + '</div>';
  }

  function donut(value, semCls, opts) {
    opts = opts || {};
    var size = opts.size || 48, sw = opts.sw || 5.5;
    var c = size / 2, r = (size - sw) / 2, circ = 2 * Math.PI * r;
    var frac = value == null ? 0 : Math.max(0, Math.min(1, value / 100));
    var dash = circ * frac;
    var col = semCls ? "var(--" + semCls + ")" : "var(--neutro)";
    var txt = opts.text != null ? opts.text : (value == null ? "—" : Math.round(value) + "%");
    return '<svg class="donut" width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '" aria-hidden="true">' +
      '<circle cx="' + c + '" cy="' + c + '" r="' + r + '" fill="none" stroke="var(--line)" stroke-width="' + sw + '"/>' +
      '<circle cx="' + c + '" cy="' + c + '" r="' + r + '" fill="none" stroke="' + col + '" stroke-width="' + sw + '" ' +
      'stroke-linecap="round" stroke-dasharray="' + dash.toFixed(1) + ' ' + (circ - dash).toFixed(1) + '" ' +
      'transform="rotate(-90 ' + c + ' ' + c + ')"/>' +
      '<text x="' + c + '" y="' + c + '" text-anchor="middle" dominant-baseline="central" class="donut__t">' + esc(txt) + '</text>' +
      '</svg>';
  }

  /* ------------------------- identidad del jugador --------------------- */
  var LS_KEY = "gps-jugador";
  function resolveDorsal() {
    var u = new URLSearchParams(location.search);
    var q = u.get("j") || u.get("jugador");
    if (q != null && q !== "") {
      try { localStorage.setItem(LS_KEY, q); } catch (e) {}
      return parseInt(q, 10);
    }
    try { var s = localStorage.getItem(LS_KEY); if (s) return parseInt(s, 10); } catch (e) {}
    return null;
  }
  function refPlayer(dorsal) { return DATA.refPartido.players.find(function (p) { return p.dorsal === dorsal; }); }

  var DORSAL = resolveDorsal();
  var ME = DORSAL != null ? refPlayer(DORSAL) : null;

  var state = { micro: MICROS[0], screen: "sesion", session: null };

  /* --------------------------- gate (sin identidad) ------------------- */
  function renderGate() {
    document.getElementById("microMeta").innerHTML = "";
    document.getElementById("nav").style.display = "none";
    document.getElementById("playerName").textContent = "MIS DATOS GPS";
    var c = document.getElementById("crest");
    c.className = "crest crest--club"; c.innerHTML = '<img src="icons/escudo.png?v=36" alt="">';
    var opts = DATA.refPartido.players.slice()
      .sort(function (a, b) { return a.dorsal - b.dorsal; })
      .map(function (p) { return '<option value="' + p.dorsal + '">#' + p.dorsal + " · " + esc(p.jugador) + "</option>"; }).join("");
    view.innerHTML =
      '<div class="gate">' +
      '<div class="crest"><img src="icons/escudo.png" alt="Atlético Baleares"></div>' +
      '<h2>Acceso del jugador</h2>' +
      '<p class="muted" style="max-width:280px">Pídele a tu preparador físico el enlace con tu acceso. ' +
      'Para probar la app puedes elegir un jugador de la lista:</p>' +
      '<select id="gateSel"><option value="">— elegir jugador —</option>' + opts + '</select>' +
      '</div>';
    document.getElementById("gateSel").addEventListener("change", function () {
      if (!this.value) return;
      try { localStorage.setItem(LS_KEY, this.value); } catch (e) {}
      location.search = "?j=" + this.value;
    });
  }

  function inits(name) {
    var p = String(name || "").split(",");
    return (p[0].trim().slice(0, 1) + (p[1] ? p[1].trim().slice(0, 1) : "")).toUpperCase();
  }
  function photoHTML(dorsal, name) {
    return '<span class="crest__ini">' + esc(inits(name)) + '</span>' +
      '<img src="fotos/' + dorsal + '.png?v=36" alt="" ' +
      'onerror="this.parentNode.classList.add(\'is-empty\');this.remove()">';
  }

  /* --------------------------- topbar ------------------------------- */
  function renderTopbar() {
    document.getElementById("playerName").textContent = ME.jugador + "  ·  #" + ME.dorsal;
    document.getElementById("crest").innerHTML = photoHTML(ME.dorsal, ME.jugador);
    var meta = DATA[state.micro].meta || {};
    var estado = meta.estado === "activo" ? "EN CURSO" : "CERRADO";
    document.getElementById("microMeta").innerHTML =
      '<span><b>' + esc(meta.titulo || state.micro) + (meta.tipo ? ' · Tipo ' + esc(meta.tipo) : '') + '</b> · ' + estado + '</span>' +
      '<span>' + esc(meta.semana || "") + '</span>' +
      '<span>Último cálculo <b>' + esc(meta.calculoFecha || "—") + '</b></span>';
    document.getElementById("topbarSub").textContent =
      ((DATA.meta && DATA.meta.club) || "Carga GPS") + " · " + (meta.temporada || "");
  }
  function mk(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }

  /* ------------------------- componente métrica --------------------- */
  function mrow(label, unit, me, obj, team, meDec) {
    var sem = semaphore(me, obj);
    var scale = Math.max(me || 0, obj || 0, team || 0) * 1.12 || 1;
    var meW = me != null ? Math.max(2, Math.min(100, me / scale * 100)) : 0;
    var objL = obj != null ? Math.max(0, Math.min(100, obj / scale * 100)) : null;
    var f = meDec ? function (v) { return fmtDec(v, meDec); } : fmt;

    var cmpObj = obj != null ? '<span>obj <b>' + signed(pct(me, obj)) + '</b></span>' : "";
    var cmpTeam = team != null ? '<span>equipo <b>' + signed(pct(me, team)) + '</b></span>' : "";

    return '<div class="mrow">' +
      '<div class="mrow__head"><span class="mrow__label">' + esc(label) + (unit ? '<span class="mrow__unit">' + esc(unit) + '</span>' : '') + '</span>' +
      '<span class="mrow__cmp">' + cmpObj + (cmpObj && cmpTeam ? ' · ' : '') + cmpTeam + '</span></div>' +
      '<div class="mrow__vals">' +
      '<div class="mv mv--me"><span class="mv__n ' + (sem || "") + '">' + (me != null ? f(me) : "—") + '</span><span class="mv__k">tú</span></div>' +
      '<div class="mv"><span class="mv__n">' + (obj != null ? f(obj) : "—") + '</span><span class="mv__k">objetivo</span></div>' +
      '<div class="mv mv--team"><span class="mv__n">' + (team != null ? f(team) : "—") + '</span><span class="mv__k">media equipo</span></div>' +
      '</div>' +
      objBar(meW, objL, sem) +
      '</div>';
  }
  // barra de cumplimiento: relleno hasta lo conseguido (color = semáforo),
  // franja verde = ±10 % del objetivo, tick + triángulo = objetivo, bolita = dónde ha llegado.
  function objBar(meW, objL, sem) {
    if (objL == null) return "";
    var lo = Math.max(0, objL * 0.9).toFixed(1);
    var hi = Math.min(100, objL * 1.1).toFixed(1);
    return '<div class="obar" style="--me:' + meW.toFixed(1) + '%;--obj:' + objL.toFixed(1) + '%;--lo:' + lo + '%;--hi:' + hi + '%">' +
      '<div class="obar__track"><span class="obar__zone"></span><span class="obar__fill ' + (sem || "") + '"></span></div>' +
      '<span class="obar__obj"></span><span class="obar__end ' + (sem || "") + '"></span></div>';
  }
  function noteHtml(t) {
    if (!t) return "";
    return esc(t).replace(/LEYENDA/g, "<b>LEYENDA</b>").replace(/REHAB|N\/A/g, "<b>$&</b>");
  }
  function estadoBanner(estado) {
    if (estado === "rehab") return '<div class="alert alert--info">' + iconWarn() +
      '<div><b>Trabajo individual (rehab).</b> Tus datos se muestran como informativos: sin objetivo y sin comparación con la media del equipo.</div></div>';
    if (estado === "na") return '<div class="alert alert--info">' + iconWarn() +
      '<div><b>No participaste en esta sesión.</b></div></div>';
    if (estado === "na-match") return '<div class="alert alert--info">' + iconWarn() +
      '<div><b>No jugaste este partido.</b></div></div>';
    if (estado === "parcial") return '<div class="alert alert--ok">' + iconOk() +
      '<div><b>Participación parcial.</b> Se compara con normalidad; ten en cuenta la menor duración.</div></div>';
    return "";
  }

  /* ----------------------------- SESIÓN ------------------------------- */
  function screenSesion() {
    var m = DATA[state.micro];
    var keys = sessionKeys(m);
    if (!state.session || keys.indexOf(state.session) < 0) state.session = lastCompletedKey(m);
    var s = getSession(m, state.session);
    var match = isMatch(m, state.session);
    var p = s.players.find(function (x) { return x.dorsal === DORSAL; });
    var done = isCompleted(s);
    var estado = p && p.estado;
    var teamOf = function (mm) { return done && s.teamAvg && s.teamAvg[mm] ? s.teamAvg[mm].real : null; };

    var pills = '<div class="pills">' + keys.map(function (k) {
      var ss = getSession(m, k);
      return '<button class="pill' + (k === state.session ? " is-active" : "") + (isCompleted(ss) ? "" : " is-pending") +
        (isMatch(m, k) ? " is-match" : "") + '" data-session="' + k + '">' + k +
        '<small>' + esc(isMatch(m, k) ? ("vs " + (ss.rival || "Partido")).slice(0, 14) : roleShort(sessionRole(ss))) + '</small></button>';
    }).join("") + '</div>';

    var head = '<div class="card"><div class="card__title">' +
      (match ? 'Partido ' + state.session : 'Sesión ' + state.session) +
      ' <span class="count">' + esc(match ? ('vs ' + (s.rival || '—')) : roleShort(sessionRole(s))) + ' · ' + esc(fdate(s.date)) + '</span></div>';

    if (!done) head += '<div class="muted" style="margin-bottom:10px">' +
      (match ? 'Partido previsto. Aún sin datos.' : 'Sesión prevista. Aún sin datos: se muestran solo tus objetivos.') + '</div>';
    else if (match) head += '<div class="muted" style="margin-bottom:10px">Un partido no lleva objetivo: se compara tu dato con la media del equipo.</div>';
    if (estado === "na") head += estadoBanner(match ? "na-match" : "na") + '<div style="height:10px"></div>';

    var rows = "";
    if (estado !== "na") {
      rows = METRICS.map(function (mm) {
        var c = p ? p[mm.key] : null;
        var me = c ? c.real : null;
        var obj = (match || estado === "rehab") ? null : (c ? c.obj : null);
        return mrow(mm.label, mm.unit, me, obj, teamOf(mm.key), 0);
      }).join("");
    }

    var info = "";
    if (p && estado !== "na") {
      info = '<div class="info-metrics">' +
        kpi((p.velMax != null ? fmtDec(p.velMax, 1) : "—"), "Vel. máx km/h", s.teamAvg && s.teamAvg.velMax != null ? "equipo " + fmtDec(s.teamAvg.velMax, 1) : "") +
        kpi(fmt(p.playerLoad), "Player Load", s.teamAvg && s.teamAvg.playerLoad != null ? "equipo " + fmt(s.teamAvg.playerLoad) : "") +
        kpi((p.duracion || "—"), "Duración", "") +
        '</div>';
    }

    var note = s.nota ? '<div class="note" style="margin-top:12px">' + noteHtml(s.nota) + '</div>' : '';
    return pills + head + rows + info + note + '</div>';
  }

  function fdate(iso) {
    if (!iso) return "—";
    var p = iso.split("-");
    return p[2] + "/" + p[1] + "/" + p[0];
  }

  function kpi(num, label, sub) {
    return '<div class="kpi"><div class="kpi__num">' + num + '</div><div class="kpi__label">' + esc(label) + '</div>' +
      (sub ? '<div class="muted" style="font-size:10px;margin-top:2px">' + esc(sub) + '</div>' : '') + '</div>';
  }

  /* ---------------------------- MICROCICLO ---------------------------- */
  function screenMicro() {
    var m = DATA[state.micro];
    var co = m.cargasObjetivo;
    var p = co.players.find(function (x) { return x.dorsal === DORSAL; });
    var ta = co.teamAvg;
    var sesKeys = sessionKeys(m).filter(function (k) { return !/^PT\d+$/.test(k); });
    var total = sesKeys.length;
    var pend = sesKeys.filter(function (k) { return !isCompleted(getSession(m, k)); })
      .map(function (k) { return k + " " + roleShort(sessionRole(getSession(m, k))); });

    var rows = METRICS.map(function (mm) {
      var c = p ? p[mm.key] : null;
      var t = ta[mm.key] || {};
      return mrow(mm.label, mm.unit, c ? c.real : null, c ? c.obj : null, t.real != null ? t.real : null, 0);
    }).join("");

    return '<div class="card">' +
      '<div class="card__title">Microciclo en curso <span class="count">acumulado · ' + total + ' sesiones</span></div>' +
      '<div class="muted" style="margin-bottom:12px">Objetivo acumulado de las <b>' + total + ' sesiones de entrenamiento</b> de la semana (sin el partido) frente a lo que llevas hecho. ' +
      'El azul indica carga que <b>aún te falta</b> por completar.' +
      (pend.length ? ' Te faltan: <b>' + esc(pend.join(" · ")) + '</b>.' : ' Sesiones completas.') + '</div>' +
      rows +
      (co.nota ? '<div class="note" style="margin-top:12px">' + noteHtml(co.nota) + '</div>' : '') +
      '</div>';
  }

  /* ---------------------------- CARGA A:C ----------------------------- */
  function screenCargaAC() {
    var m = DATA[state.micro];
    var ac = m.cargaAC;
    var p = ac.players.find(function (x) { return x.dorsal === DORSAL; });
    var ta = ac.teamAvg || {};
    if (!p) return '<div class="card"><p class="muted">Sin datos de carga para este microciclo.</p></div>';

    var cls = acwrClass(p.acwr), av = fmtDec(p.acwr, 2), msg;
    if (p.acwr === 0) msg = '<div class="alert">' + iconWarn() + '<div><b>ACWR 0,00.</b> No acumulas Player Load en los últimos 7 días. Habla con tu preparador sobre tu reintroducción progresiva.</div></div>';
    else if (cls === "high") msg = '<div class="alert">' + iconWarn() + '<div><b>ACWR ' + av + '.</b> Por encima de 1,50: riesgo de sobrecarga, tu carga reciente ha subido muy rápido respecto a tu media.</div></div>';
    else if (cls === "warn") msg = '<div class="alert alert--ok">' + iconWarn() + '<div><b>ACWR ' + av + '.</b> Entre 1,31 y 1,50: precaución, vigila el volumen de los próximos días.</div></div>';
    else if (cls === "low") msg = '<div class="alert alert--info">' + iconWarn() + '<div><b>ACWR ' + av + '.</b> Por debajo de 0,80: infracarga respecto a tu media.</div></div>';
    else msg = '<div class="alert alert--ok">' + iconOk() + '<div><b>ACWR ' + av + '.</b> Dentro de la zona óptima (0,80–1,30).</div></div>';

    var curSes = {};
    sessionKeys(m).forEach(function (k) { curSes[k] = 1; });
    var chart = (p.serie && ac.serieDias)
      ? '<div style="margin:16px 0 2px" class="section-label">Últimos 28 días</div>' + acwrChart(p.serie, ac.serieDias, curSes)
      : "";

    return '<div class="card">' +
      '<div class="card__title">Tu carga aguda·crónica</div>' +
      '<div class="stat-hero">' +
      '<div class="stat-hero__num">' + fmtDec(p.acwr, 2) + '</div>' +
      '<div class="stat-hero__label">ACWR de hoy · zona óptima 0,80–1,30 · media del equipo ' + fmtDec(ta.acwr, 2) + '</div>' +
      '</div>' +
      '<div class="kpi-row" style="margin-top:12px">' +
      kpi(fmt(p.cargaAguda), "Carga aguda · media 7 d", ta.cargaAguda != null ? "equipo " + fmt(ta.cargaAguda) : "") +
      kpi(fmt(p.cargaCronica), "Carga crónica · media 28 d", ta.cargaCronica != null ? "equipo " + fmt(ta.cargaCronica) : "") +
      '</div>' +
      chart +
      '<div style="margin-top:14px">' + msg + '</div>' +
      '<div class="note" style="margin-top:12px">Cada columna es tu Player Load de ese día (los días sin entrenamiento cuentan como 0). ' +
      'La línea azul es la media de los últimos 7 días (aguda); la dorada, la de los últimos 28 (crónica). ' +
      'El punto de abajo es tu ACWR de cada día = aguda ÷ crónica.</div>' +
      '</div>';
  }

  function acwrChart(serie, dias, curSes, barSem, bandLabel, clip, sesLabels) {
    curSes = curSes || {};
    barSem = barSem || null;
    if (clip != null) {
      var from, to;
      if (typeof clip === "number") { from = Math.max(0, dias.length - clip); to = dias.length - 1; }
      else { from = Math.max(0, clip.from | 0); to = Math.min(dias.length - 1, clip.to | 0); }
      if (to >= from && (from > 0 || to < dias.length - 1)) {
        serie = {
          pl: serie.pl.slice(from, to + 1), aguda: serie.aguda.slice(from, to + 1),
          cronica: serie.cronica.slice(from, to + 1), acwr: serie.acwr.slice(from, to + 1),
          ses: serie.ses.slice(from, to + 1)
        };
        dias = dias.slice(from, to + 1);
      }
    }
    var micro = !!sesLabels;
    var n = serie.pl.length;

    /* ----- modo microciclo: un solo panel, columnas PL + ACWR integrado ----- */
    if (micro) {
      var mColW = 38, mPadL = 30, mPadR = 28;
      var mW = mPadL + n * mColW + mPadR;
      var mmT = 14, mmH = 158, mxH = 30;
      var mHt = mmT + mmH + mxH;
      var mcx = function (i) { return mPadL + mColW * (i + 0.5); };

      var mRawMax = Math.max.apply(null, serie.pl) || 1;
      var mMaxY = Math.max(50, Math.ceil(mRawMax * 1.12 / 50) * 50);
      var mY = function (v) { return mmT + mmH - (v / mMaxY) * mmH; };

      var mChartW = n * mColW, mBw = 0.56 * mColW;
      var mBaseY = mmT + mmH;

      var mAcc = serie.acwr.filter(function (v) { return v > 0; });
      var mLo = mAcc.length ? Math.min.apply(null, mAcc) : 0.8;
      var mHi = mAcc.length ? Math.max.apply(null, mAcc) : 1.3;
      var mMinA = Math.max(0.3, Math.min(mLo - 0.15, 0.7));
      var mMaxA = Math.min(2.0, Math.max(mHi + 0.15, 1.45));
      var mA = function (v) {
        v = Math.max(mMinA, Math.min(mMaxA, v));
        var y = mmT + mmH - ((v - mMinA) / (mMaxA - mMinA)) * mmH;
        return Math.max(mmT + 4, Math.min(mBaseY - 3, y));
      };

      var mBars = serie.pl.map(function (v, i) {
        if (!v) return "";
        var sk = serie.ses[i];
        var sem = barSem && sk && barSem[sk];
        var fill = sem ? "var(--" + sem + ")" : "var(--azul)";
        return '<rect x="' + (mcx(i) - mBw / 2).toFixed(1) + '" y="' + mY(v).toFixed(1) + '" width="' + mBw.toFixed(1) +
          '" height="' + (mBaseY - mY(v)).toFixed(1) + '" rx="2" style="fill:' + fill + ';opacity:' + (sem ? ".88" : ".38") + '"/>';
      }).join("");

      var mZone = '<rect x="' + mPadL + '" y="' + mA(1.3).toFixed(1) + '" width="' + mChartW + '" height="' + (mA(0.8) - mA(1.3)).toFixed(1) +
        '" style="fill:var(--sem-verde-bg);opacity:.7"/>';
      var mRef = '<line x1="' + mPadL + '" x2="' + (mW - mPadR) + '" y1="' + mA(1).toFixed(1) + '" y2="' + mA(1).toFixed(1) +
        '" style="stroke:var(--neutro);stroke-dasharray:3 3"/>';
      var mAxes =
        '<line x1="' + mPadL + '" x2="' + mPadL + '" y1="' + mmT + '" y2="' + mBaseY + '" style="stroke:var(--line)"/>' +
        '<line x1="' + (mW - mPadR) + '" x2="' + (mW - mPadR) + '" y1="' + mmT + '" y2="' + mBaseY + '" style="stroke:var(--line)"/>' +
        '<line x1="' + mPadL + '" x2="' + (mW - mPadR) + '" y1="' + mBaseY + '" y2="' + mBaseY + '" style="stroke:var(--line)"/>';

      var mXl = dias.map(function (iso, i) {
        var sk = serie.ses[i]; if (!sk) return "";
        var lx = mcx(i).toFixed(1);
        return '<line x1="' + lx + '" x2="' + lx + '" y1="' + mmT + '" y2="' + mBaseY + '" style="stroke:var(--line);stroke-dasharray:2 2;opacity:.5"/>' +
          '<text class="ax-t" x="' + lx + '" y="' + (mBaseY + 14) + '" text-anchor="middle">' + esc((sesLabels && sesLabels[sk]) || "") + '</text>' +
          '<text class="ax-d" x="' + lx + '" y="' + (mBaseY + 24) + '" text-anchor="middle">' + (+iso.slice(8)) + "/" + (+iso.slice(5, 7)) + '</text>';
      }).join("");

      var mYlab =
        '<text class="ax-v" x="' + (mPadL - 4) + '" y="' + (mmT + 4) + '" text-anchor="end">' + fmt(mMaxY) + '</text>' +
        '<text class="ax-v" x="' + (mPadL - 4) + '" y="' + mBaseY + '" text-anchor="end">0</text>';
      var mAlab =
        '<text class="ax-v" x="' + (mW - mPadR + 4) + '" y="' + (mA(1.3) + 3).toFixed(1) + '">1,3</text>' +
        '<text class="ax-v" x="' + (mW - mPadR + 4) + '" y="' + (mA(1.0) + 3).toFixed(1) + '">1,0</text>' +
        '<text class="ax-v" x="' + (mW - mPadR + 4) + '" y="' + (mA(0.8) + 3).toFixed(1) + '">0,8</text>';

      var mLine = '<path d="' + serie.acwr.map(function (v, i) { return (i ? "L" : "M") + mcx(i).toFixed(1) + " " + mA(v).toFixed(1); }).join(" ") +
        '" style="fill:none;stroke:var(--ink);stroke-width:2;opacity:.65"/>';
      var mDots = serie.acwr.map(function (v, i) {
        var c = v === 0 ? "var(--neutro)" : v < 0.8 ? "var(--sem-azul)"
          : v > 1.5 ? "var(--sem-rojo)" : v > 1.3 ? "var(--sem-naranja)" : "var(--sem-verde)";
        return '<circle cx="' + mcx(i).toFixed(1) + '" cy="' + mA(v).toFixed(1) + '" r="3.4" style="fill:' + c + ';stroke:var(--surface);stroke-width:1.4"/>';
      }).join("");

      return '<div style="margin:0 -8px">' +
        '<svg class="acwrc acwrc--m" viewBox="0 0 ' + mW + ' ' + mHt + '" preserveAspectRatio="xMidYMid meet" style="width:100%;display:block">' +
        mZone + mRef + mAxes + mBars + mXl + mLine + mDots + mYlab + mAlab +
        '</svg></div>' +
        '<div class="radar-legend" style="flex-wrap:wrap;gap:8px 14px;margin-top:8px">' +
        '<span><b style="display:inline-block;width:10px;height:10px;background:var(--azul);border-radius:2px;vertical-align:middle;margin-right:6px"></b>Player Load</span>' +
        '<span><b style="display:inline-block;width:14px;border-top:2.5px solid var(--ink);vertical-align:middle;margin-right:6px"></b>ACWR (eje dcho.)</span>' +
        '<span><b style="display:inline-block;width:10px;height:10px;background:var(--sem-verde-bg);border:1px solid var(--verde);border-radius:2px;vertical-align:middle;margin-right:6px"></b>Zona 0,80–1,30</span>' +
        '</div>' +
        '<div class="muted" style="font-size:10.5px;margin-top:4px">Cada columna es el Player Load de esa sesión, coloreada según el semáforo de cumplimiento de objetivos (los partidos, en gris). La línea con puntos es el ACWR de cada día.</div>';
    }

    var colW = micro ? Math.max(26, Math.min(40, Math.round(240 / n))) : 14;
    var padL = micro ? 26 : 30, padR = micro ? 8 : 12;
    var W = padL + n * colW + padR;
    var mT = 12, mH = micro ? 124 : 118, sGap = micro ? 34 : 26;
    var sH = micro ? 96 : 82;
    var sT = mT + mH + sGap;
    var H = sT + sH + (micro ? 10 : 22);
    var cx = function (i) { return padL + colW * (i + 0.5); };

    var rawMax = Math.max.apply(null, serie.pl.concat(serie.aguda, serie.cronica)) || 1;
    var maxY = Math.max(50, Math.ceil(rawMax * 1.08 / 50) * 50);
    var my = function (v) { return mT + mH - (v / maxY) * mH; };
    var accv = serie.acwr.filter(function (v) { return v > 0; });
    var aLo = accv.length ? Math.min.apply(null, accv) : 0.8;
    var aHi = accv.length ? Math.max.apply(null, accv) : 1.3;
    var minA = Math.max(0, Math.min(aLo - 0.12, 0.74));
    var maxA = Math.min(2.8, Math.max(aHi + 0.12, 1.36));
    var sy = function (v) { v = Math.max(minA, Math.min(maxA, v)); return sT + sH - ((v - minA) / (maxA - minA)) * sH; };
    function path(a, f) { return a.map(function (v, i) { return (i ? "L" : "M") + cx(i).toFixed(1) + " " + f(v).toFixed(1); }).join(" "); }

    var bw = (micro ? 0.56 : 0.62) * colW;
    var bars = serie.pl.map(function (v, i) {
      if (!v) return "";
      var sk = serie.ses[i];
      var sem = barSem && sk && barSem[sk];
      var fill = sem ? "var(--" + sem + ")" : "var(--azul)";
      var op = sem ? ".92" : ".42";
      return '<rect x="' + (cx(i) - bw / 2).toFixed(1) + '" y="' + my(v).toFixed(1) + '" width="' + bw.toFixed(1) +
        '" height="' + (mT + mH - my(v)).toFixed(1) + '" rx="1.5" style="fill:' + fill + ';opacity:' + op + '"/>';
    }).join("");

    var band = '<rect x="' + padL + '" y="' + sy(1.3).toFixed(1) + '" width="' + (n * colW) + '" height="' + (sy(0.8) - sy(1.3)).toFixed(1) + '" style="fill:var(--sem-verde-bg)"/>';
    var ref1 = '<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + sy(1).toFixed(1) + '" y2="' + sy(1).toFixed(1) + '" style="stroke:var(--neutro);stroke-dasharray:3 3"/>';
    var axes =
      '<line x1="' + padL + '" x2="' + padL + '" y1="' + mT + '" y2="' + (mT + mH) + '" style="stroke:var(--line)"/>' +
      '<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + (mT + mH) + '" y2="' + (mT + mH) + '" style="stroke:var(--line)"/>' +
      '<line x1="' + padL + '" x2="' + padL + '" y1="' + sT + '" y2="' + (sT + sH) + '" style="stroke:var(--line)"/>';

    var yl =
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (mT + 4) + '" text-anchor="end">' + fmt(maxY) + '</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (mT + mH) + '" text-anchor="end">0</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (sy(1.3) + 3).toFixed(1) + '" text-anchor="end">1,3</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (sy(1.0) + 3).toFixed(1) + '" text-anchor="end">1,0</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (sy(0.8) + 3).toFixed(1) + '" text-anchor="end">0,8</text>';

    var xl = dias.map(function (iso, i) {
      var out = "", sk = serie.ses[i], lx = cx(i).toFixed(1);
      if (micro) {
        if (!sk) return "";
        out += '<line x1="' + lx + '" x2="' + lx + '" y1="' + mT + '" y2="' + (mT + mH) + '" style="stroke:var(--line);stroke-dasharray:2 2"/>';
        out += '<text class="ax-t" x="' + lx + '" y="' + (mT + mH + 13) + '" text-anchor="middle">' + esc((sesLabels && sesLabels[sk]) || "") + '</text>';
        out += '<text class="ax-d" x="' + lx + '" y="' + (mT + mH + 22) + '" text-anchor="middle">' + (+iso.slice(8)) + "/" + (+iso.slice(5, 7)) + '</text>';
      } else {
        if (i % 7 === 0 || i === n - 1) {
          out += '<text class="ax-v" x="' + lx + '" y="' + (H - 8) + '" text-anchor="middle">' + (+iso.slice(8)) + "/" + (+iso.slice(5, 7)) + '</text>';
        }
        if (sk) out += '<line x1="' + lx + '" x2="' + lx + '" y1="' + mT + '" y2="' + (mT + mH) + '" style="stroke:var(--line);stroke-dasharray:2 2"/>';
      }
      return out;
    }).join("");

    var micBand = "";
    if (!micro) {
      var curIdx = serie.ses.map(function (s, i) { return curSes[s] ? i : -1; }).filter(function (i) { return i >= 0; });
      if (curIdx.length) {
        var a = cx(curIdx[0]) - colW * 0.5, b = cx(curIdx[curIdx.length - 1]) + colW * 0.5;
        micBand = '<rect x="' + a.toFixed(1) + '" y="' + mT + '" width="' + (b - a).toFixed(1) + '" height="' + mH +
          '" style="fill:var(--azul);opacity:.08"/>' +
          '<text class="ax-band" x="' + ((a + b) / 2).toFixed(1) + '" y="' + (mT + mH + 11) + '" text-anchor="middle">' + esc(bandLabel || state.micro) + '</text>';
      }
    }

    var dac = serie.acwr.map(function (v, i) {
      var c = v === 0 ? "var(--neutro)" : v < 0.8 ? "var(--sem-azul)"
        : v > 1.5 ? "var(--sem-rojo)" : v > 1.3 ? "var(--sem-naranja)" : "var(--sem-verde)";
      return '<circle cx="' + cx(i).toFixed(1) + '" cy="' + sy(v).toFixed(1) + '" r="3.4" style="fill:' + c + '"/>';
    }).join("");

    return '<div style="margin:0 -6px">' +
      '<svg class="acwrc acwrc--w" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet" style="width:100%;display:block">' +
      micBand + band + ref1 + axes + bars +
      '<path d="' + path(serie.cronica, my) + '" style="fill:none;stroke:var(--oro);stroke-width:2.6;stroke-dasharray:5 3"/>' +
      '<path d="' + path(serie.aguda, my) + '" style="fill:none;stroke:var(--azul);stroke-width:2.8"/>' +
      '<path d="' + path(serie.acwr, sy) + '" style="fill:none;stroke:var(--txt-2);stroke-width:2.2"/>' +
      dac + yl + xl +
      '</svg></div>' +
      '<div class="radar-legend" style="flex-wrap:wrap;gap:8px 14px;margin-top:8px">' +
      '<span><b style="display:inline-block;width:10px;height:10px;background:var(--azul);border-radius:2px;vertical-align:middle;margin-right:6px"></b>Player Load</span>' +
      '<span><b style="display:inline-block;width:14px;border-top:3px solid var(--azul);vertical-align:middle;margin-right:6px"></b>Aguda 7 d</span>' +
      '<span><b style="display:inline-block;width:14px;border-top:3px dashed var(--oro);vertical-align:middle;margin-right:6px"></b>Crónica 28 d</span>' +
      '<span><b style="display:inline-block;width:10px;height:10px;background:var(--sem-verde-bg);border:1px solid var(--verde);border-radius:2px;vertical-align:middle;margin-right:6px"></b>ACWR · zona 0,80–1,30</span>' +
      '</div>' +
      (barSem ? '<div class="muted" style="font-size:10.5px;margin-top:4px">Cada columna de Player Load va coloreada según el semáforo de cumplimiento de objetivos de esa sesión; las de los partidos van en gris (no llevan objetivo).</div>' : '');
  }

  /* ------------------------------ PERFIL ----------------------------- */
  function screenPerfil() {
    var t = DATA.refPartido.teamAvg || {};
    var axes = RADAR.map(function (mm) {
      return { name: mm.short, label: mm.label, me: ME[mm.key], team: t[mm.key], dec: mm.dec || 0, unit: mm.unit };
    }).filter(function (a) { return a.team; });

    var table = '<div class="tablewrap" style="margin-top:12px"><table class="grid">' +
      '<thead><tr><th class="col-player">Métrica</th><th>Tú</th><th>Equipo</th><th>Dif.</th></tr></thead><tbody>' +
      RADAR.map(function (mm) {
        var me = ME[mm.key], tv = t[mm.key];
        var f = (mm.dec ? function (v) { return fmtDec(v, mm.dec); } : fmt);
        return '<tr><td class="col-player">' + esc(mm.label) + ' <span class="obj">' + (mm.unit || "") + '</span></td>' +
          '<td class="num">' + f(me) + '</td><td class="num">' + f(tv) + '</td>' +
          '<td class="num">' + signed(pct(me, tv)) + '</td></tr>';
      }).join("") +
      '</tbody></table></div>';

    var gkNote = (ME.partidos || 0) < 2
      ? '<div class="note" style="margin-top:10px">Todavía tienes pocos partidos de referencia (' + (ME.partidos || 0) + '): tu REF_PARTIDO puede cambiar bastante con los próximos.</div>'
      : '';

    return '<div class="card">' +
      '<div class="card__title">Tu perfil de partido <span class="count">media de ' + (ME.partidos || 0) + ' partido' + ((ME.partidos || 0) === 1 ? '' : 's') + '</span></div>' +
      '<div class="muted" style="margin-bottom:10px">Tu REF_PARTIDO (media de tus partidos estimados a 95′) frente a la media del equipo.</div>' +
      '<div class="radar-wrap">' + radarSVG(axes) +
      '<div class="radar-legend"><span><i class="me"></i>Tú</span><span><i class="team"></i>Media equipo</span></div>' +
      '</div>' +
      table + gkNote +
      (DATA.refPartido.nota ? '<div class="note" style="margin-top:12px">' + noteHtml(DATA.refPartido.nota) + '</div>' : '') +
      '</div>';
  }

  function radarSVG(axes) {
    var N = axes.length, cx = 160, cy = 148, R = 100, teamR = R * 0.55;
    function ang(i) { return -Math.PI / 2 + i * 2 * Math.PI / N; }
    function P(i, r) { return [(cx + r * Math.cos(ang(i))).toFixed(1), (cy + r * Math.sin(ang(i))).toFixed(1)]; }
    function poly(rs) { return axes.map(function (a, i) { return P(i, rs[i]).join(","); }).join(" "); }

    var rings = [0.28, 0.55, 0.82, 1].map(function (f) {
      return '<polygon class="grid-poly" points="' + axes.map(function (a, i) { return P(i, R * f).join(","); }).join(" ") + '"' +
        (f === 0.55 ? ' style="stroke:var(--oro);opacity:.35"' : '') + '/>';
    }).join("");
    var spokes = axes.map(function (a, i) { var e = P(i, R); return '<line class="spoke" x1="' + cx + '" y1="' + cy + '" x2="' + e[0] + '" y2="' + e[1] + '"/>'; }).join("");

    var teamPoly = '<polygon class="team-poly" points="' + poly(axes.map(function () { return teamR; })) + '"/>';
    var meR = axes.map(function (a) {
      if (a.me == null || !a.team) return 6;
      return Math.max(6, Math.min(R, teamR * (a.me / a.team)));
    });
    var mePoly = '<polygon class="me-poly" points="' + poly(meR) + '"/>';
    var meDots = axes.map(function (a, i) { var q = P(i, meR[i]); return '<circle class="me-dot" cx="' + q[0] + '" cy="' + q[1] + '" r="2.6"/>'; }).join("");

    var labels = axes.map(function (a, i) {
      var q = P(i, R + 15), x = +q[0], y = +q[1];
      var anchor = Math.abs(x - cx) < 8 ? "middle" : (x < cx ? "end" : "start");
      var f = a.dec ? fmtDec(a.me, a.dec) : fmt(a.me);
      return '<text class="ax-name" x="' + x + '" y="' + (y - 2) + '" text-anchor="' + anchor + '">' + esc(a.name) + '</text>' +
        '<text class="ax-val" x="' + x + '" y="' + (y + 9) + '" text-anchor="' + anchor + '">' + f + '</text>';
    }).join("");

    return '<svg class="radar" viewBox="0 0 320 300" role="img" aria-label="Gráfica de telaraña de tu perfil frente a la media del equipo">' +
      rings + spokes + teamPoly + mePoly + meDots + labels + '</svg>';
  }

  /* ----------------------------- HISTORIAL --------------------------- */
  function screenHistorial() {
    var html = '<div class="card"><div class="card__title">Historial de microciclos</div>' +
      '<div class="muted" style="margin-bottom:12px">Tus datos en cada microciclo de la temporada. Toca un microciclo para desplegar su resumen.</div>' +
      '<div class="hist">';

    MICROS.forEach(function (mk, idx) {
      var m = DATA[mk];
      var meta = m.meta || {};
      var keys = sessionKeys(m);
      var sesKeys = keys.filter(function (k) { return !isMatch(m, k); });
      var matchKeys = keys.filter(function (k) { return isMatch(m, k); });
      var wk = ((m.cargasSemana || m.cargasObjetivo).players || []).find(function (x) { return x.dorsal === DORSAL; }) || {};
      var so = ((m.cargasObjetivo || {}).players || []).find(function (x) { return x.dorsal === DORSAL; }) || {};
      var ac = (m.cargaAC.players || []).find(function (x) { return x.dorsal === DORSAL; }) || {};
      var closed = meta.estado !== "activo";
      var doneSes = sesKeys.filter(function (k) { return isCompleted(getSession(m, k)); }).length;

      var ratios = [];
      METRICS.forEach(function (mm) {
        var c = so[mm.key];
        if (c && c.obj && c.real != null) ratios.push(c.real / c.obj);
      });
      var cumpl = ratios.length ? Math.round(ratios.reduce(function (a, b) { return a + b; }, 0) / ratios.length * 100) : null;

      var plTot = 0, plAny = false, nNa = 0;
      keys.forEach(function (k) {
        var p = getSession(m, k).players.find(function (x) { return x.dorsal === DORSAL; });
        if (!p) return;
        if (p.estado === "na") nNa++;
        if (p.playerLoad != null) { plTot += p.playerLoad; plAny = true; }
      });

      var acwrBadge = ac.acwr != null
        ? '<span class="acwr ' + acwrClass(ac.acwr) + '">' + fmtDec(ac.acwr, 2) + '</span>'
        : '<span class="muted">—</span>';
      var pendMatch = matchKeys.filter(function (k) { return !isCompleted(getSession(m, k)); });

      // realizado en el/los partido(s) de la semana, por métrica
      var matchVals = {};
      matchKeys.forEach(function (k) {
        var mp = (getSession(m, k).players || []).find(function (x) { return x.dorsal === DORSAL; });
        if (!mp) return;
        METRICS.forEach(function (mm) {
          var v = mp[mm.key] && mp[mm.key].real;
          if (v != null) matchVals[mm.key] = (matchVals[mm.key] || 0) + v;
        });
      });
      var hasMatch = matchKeys.some(function (k) { return isCompleted(getSession(m, k)); });

      // círculo de cumplimiento (semáforo del objetivo de sesiones)
      var cumplSem = cumpl != null ? semaphore(cumpl, 100) : null;
      var donutHTML = cumpl != null
        ? donut(cumpl, cumplSem)
        : donut(sesKeys.length ? doneSes / sesKeys.length * 100 : 0, null, { text: doneSes + '/' + sesKeys.length });
      var subStatus = !closed
        ? (doneSes < sesKeys.length ? 'En curso · ' + doneSes + '/' + sesKeys.length + ' sesiones'
           : (pendMatch.length ? 'Falta el partido' : 'En curso'))
        : 'Cerrado';

      var chips = '<div class="hist__chips">' +
        '<span class="chipv">ACWR al cierre ' + acwrBadge + '</span>' +
        (plAny ? '<span class="chipv">PL total semana <b>' + fmt(plTot) + '</b></span>' : '') +
        (cumpl != null
          ? '<span class="chipv">Objetivo de sesiones cumplido al <b>' + cumpl + '%</b></span>'
          : '<span class="chipv"><b>' + doneSes + '</b> de ' + sesKeys.length + ' sesiones hechas</span>') +
        '</div>';

      var mets = '<div class="hist-metrics">' + METRICS.map(function (mm) {
        var c = so[mm.key] || {};
        var sem = semaphore(c.real, c.obj);
        var mv = matchVals[mm.key];
        var dp = c.obj ? Math.round((c.real - c.obj) / c.obj * 100) : null;
        return '<div class="hm' + (sem ? ' ' + sem : '') + '">' +
          '<span class="hm__k">' + esc(mm.label) + ' <span class="hm__u">' + esc(mm.unit) + '</span>' +
          (dp != null ? '<span class="p' + (sem ? ' ' + sem : '') + '">' + (dp > 0 ? '+' : '') + dp + '%</span>' : '') +
          '</span>' +
          '<span class="hm__row"><span class="hm__lbl">Sesiones</span>' +
          '<span class="hm__n">' + fmt(c.real) + ' <s>/</s> ' + fmt(c.obj) + '</span></span>' +
          '<span class="hm__row hm__row--match"><span class="hm__lbl">Partido</span>' +
          '<span class="hm__n">' + (mv != null ? fmt(mv) : '—') + '</span></span>' +
          '</div>';
      }).join("") + '</div>' +
      '<div class="muted" style="font-size:11px;margin-top:2px">' +
      'Realizado en las <b>sesiones de entrenamiento</b> frente a su objetivo (color = semáforo)' +
      (hasMatch ? ', y aparte lo realizado en el partido de esa semana (sin objetivo).' : '.') +
      '</div>';

      // gráfica ACWR del microciclo con las columnas de PL coloreadas por semáforo de sesión
      var barSem = {};
      sesKeys.forEach(function (k) {
        var sp = (getSession(m, k).players || []).find(function (x) { return x.dorsal === DORSAL; });
        if (!sp) return;
        var rs = [];
        METRICS.forEach(function (mm) {
          var cc = sp[mm.key];
          if (cc && cc.obj && cc.real != null) rs.push(cc.real / cc.obj);
        });
        if (rs.length) {
          var sc = semaphore(rs.reduce(function (a, b) { return a + b; }, 0) / rs.length * 100, 100);
          if (sc) barSem[k] = sc;
        }
      });
      matchKeys.forEach(function (k) { barSem[k] = "neutro"; });
      var curMap = {};
      keys.forEach(function (k) { curMap[k] = 1; });
      var sd = m.cargaAC.serieDias || [];
      var micIdx = [];
      if (ac.serie) sd.forEach(function (iso, i) { if (curMap[ac.serie.ses[i]]) micIdx.push(i); });
      var sesLabels = {};
      keys.forEach(function (k) { sesLabels[k] = chartTag(m, k); });
      var clip = micIdx.length ? { from: micIdx[0], to: micIdx[micIdx.length - 1] } : 10;
      var chartBlock = (ac.serie && sd.length)
        ? acwrChart(ac.serie, sd, curMap, barSem, mk, clip, sesLabels)
        : '<div class="muted" style="padding:8px 0">Sin serie de carga para este microciclo.</div>';

      var flags = nNa
        ? '<div class="muted" style="font-size:11.5px">' + nNa + (nNa > 1 ? ' sesiones/partidos' : ' sesión/partido') + ' sin participar.</div>'
        : "";

      html += '<details>' +
        '<summary>' +
        '<span class="hist__ttl"><b>' + esc(meta.titulo || mk) + (meta.tipo ? ' · Tipo ' + esc(meta.tipo) : '') + '</b><span>' + esc(meta.semana || "") +
        (meta.calculoFecha ? ' · cálculo ' + esc(meta.calculoFecha) : '') + '</span>' +
        '<span class="hist__sub">' + subStatus + '</span></span>' +
        '<span class="hist__donut">' + donutHTML + '</span>' +
        '<span class="hist__chev">▾</span>' +
        '</summary>' +
        '<div class="hist__body">' + chips +
        '<div><div class="section-label" style="margin-bottom:6px">Por métrica · sesiones vs objetivo y partido</div>' + mets + '</div>' +
        '<div><div class="section-label" style="margin-bottom:6px">Player Load y ACWR del microciclo</div>' + chartBlock + '</div>' +
        flags + '</div>' +
        '</details>';
    });

    return html + '</div></div>';
  }

  /* ----------------------------- router ------------------------------ */
  var SCREENS = { sesion: screenSesion, micro: screenMicro, cargaac: screenCargaAC, perfil: screenPerfil, historial: screenHistorial };
  function render() {
    renderTopbar();
    view.innerHTML = (SCREENS[state.screen] || screenSesion)();
    view.scrollTop = 0; window.scrollTo(0, 0);
    Array.prototype.forEach.call(document.querySelectorAll(".navitem"), function (b) {
      b.classList.toggle("is-active", b.dataset.screen === state.screen);
    });
  }

  /* --------------------------- eventos ------------------------------- */
  document.getElementById("nav").addEventListener("click", function (e) {
    var b = e.target.closest(".navitem"); if (!b) return;
    state.screen = b.dataset.screen; render();
  });
  view.addEventListener("click", function (e) {
    var pill = e.target.closest(".pill[data-session]");
    if (pill) { state.session = pill.dataset.session; render(); }
  });

  /* ----------------------------- tema -------------------------------- */
  var THEME_KEY = "gps-theme";
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t || "");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", t === "dark" ? "#0E141D" : "#16345E");
  }
  try { applyTheme(localStorage.getItem(THEME_KEY) || ""); } catch (e) {}
  document.getElementById("themeBtn").addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme");
    var next = cur === "dark" ? "light" : cur === "light" ? "" : "dark";
    applyTheme(next);
    try { next ? localStorage.setItem(THEME_KEY, next) : localStorage.removeItem(THEME_KEY); } catch (e) {}
  });

  /* --------------------------- arranque ------------------------------ */
  if (!ME) { renderGate(); }
  else {
    render();
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", function () { navigator.serviceWorker.register("sw.js").catch(function () {}); });
    }
  }
})();
