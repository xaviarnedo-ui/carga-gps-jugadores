/* =========================================================================
   Carga GPS — VISTA ENTRENADOR
   Inicio · Sesión · Microciclo · Carga A:C · Partidos
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
  var CMP_COLORS = ["#2E5BAA", "#2E9E64", "#D6534A", "#8B5CF6", "#E08A2B"];

  var state = { micro: MICROS[0], screen: "inicio", session: null, cmp: [] };

  /* ----------------------------- utilidades ----------------------------- */
  var nf = new Intl.NumberFormat("es-ES");
  function fmt(v) { return (v == null) ? "—" : nf.format(Math.round(v)); }
  function fmtDec(v, d) { return (v == null) ? "—" : v.toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function el(html) { var t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstChild; }
  function pct(a, b) { return (a == null || b == null || !b) ? null : Math.round((a - b) / b * 100); }
  function signed(p) { return p == null ? "—" : (p > 0 ? "+" : "") + p + "%"; }
  function fdate(iso) { if (!iso) return "—"; var p = iso.split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }

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

  function currentMicro() { return DATA[state.micro]; }
  function sessionKeys(m) { return (m.orden || []).map(function (o) { return o.key; }); }
  function getSession(m, k) { return (m.sesiones && m.sesiones[k]) || (m.partidos && m.partidos[k]); }
  function isMatch(m, k) { return !!(m.partidos && m.partidos[k]); }
  function sessionRole(s) { return (s && s.role) || "—"; }
  function roleShort(r) { return r || "—"; }
  function isCompleted(s) { return !!(s && s.teamAvg && s.teamAvg.distancia && s.teamAvg.distancia.real != null); }
  function lastCompletedSessionKey(m) {
    var ks = sessionKeys(m), last = null;
    ks.forEach(function (k) { if (!isMatch(m, k) && isCompleted(getSession(m, k))) last = k; });
    return last || ks.filter(function (k) { return !isMatch(m, k); })[0] || ks[0];
  }
  var GRP_ORDER = { D: 0, M: 1, DL: 2, P: 3 };
  var GRP_LABEL = { D: "DEF", M: "MED", DL: "DEL", P: "POR" };
  function sortPlayers(a, b) {
    var ga = GRP_ORDER[a.grupo] != null ? GRP_ORDER[a.grupo] : 9;
    var gb = GRP_ORDER[b.grupo] != null ? GRP_ORDER[b.grupo] : 9;
    return ga !== gb ? ga - gb : a.dorsal - b.dorsal;
  }
  function refPlayer(d) { return DATA.refPartido.players.find(function (p) { return p.dorsal === d; }); }
  function roster() { return DATA.refPartido.players.slice().sort(sortPlayers); }

  function inits(name) {
    var p = String(name || "").split(",");
    return (p[0].trim().slice(0, 1) + (p[1] ? p[1].trim().slice(0, 1) : "")).toUpperCase();
  }
  function avatar(dorsal, name, cls) {
    return '<span class="avatar ' + (cls || "") + '"><span class="avatar__ini">' + esc(inits(name)) + '</span>' +
      '<img src="fotos/' + dorsal + '.png?v=37" alt="" onerror="this.parentNode.classList.add(\'is-empty\');this.remove()">' +
      '<b class="avatar__d">' + dorsal + '</b></span>';
  }
  function estadoTag(estado) {
    if (estado === "na") return '<span class="tag tag--na">No participó</span>';
    if (estado === "rehab") return '<span class="tag tag--rehab">Rehab</span>';
    if (estado === "parcial") return '<span class="tag tag--parcial">Parcial</span>';
    return "";
  }
  function iconWarn() { return '<svg viewBox="0 0 24 24" width="16" height="16"><path d="M12 3 2 20h20Zm0 6v5m0 3v.5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg>'; }
  function iconOk() { return '<svg viewBox="0 0 24 24" width="16" height="16"><path d="m4 12 5 5L20 6" stroke="currentColor" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>'; }
  function noteHtml(t) { return t ? esc(t).replace(/LEYENDA/g, "<b>LEYENDA</b>") : ""; }
  function kpi(num, label, sub) {
    return '<div class="kpi"><div class="kpi__num">' + num + '</div><div class="kpi__label">' + esc(label) + '</div>' +
      (sub ? '<div class="muted" style="font-size:10px;margin-top:2px">' + esc(sub) + '</div>' : '') + '</div>';
  }
  function legend() {
    return '<div class="legend">' +
      '<span><i class="dot azul"></i>Corto (&lt;−10%)</span>' +
      '<span><i class="dot verde"></i>Cumplido (±10%)</span>' +
      '<span><i class="dot naranja"></i>Pasado (+10/+20%)</span>' +
      '<span><i class="dot rojo"></i>Muy pasado (&gt;+20%)</span></div>';
  }

  function donut(value, semCls, opts) {
    opts = opts || {};
    var size = opts.size || 44, sw = opts.sw || 5;
    var c = size / 2, r = (size - sw) / 2, circ = 2 * Math.PI * r;
    var frac = value == null ? 0 : Math.max(0, Math.min(1, value / 100));
    var dash = circ * frac;
    var col = semCls ? "var(--" + semCls + ")" : "var(--neutro)";
    var txt = opts.text != null ? opts.text : (value == null ? "—" : Math.round(value) + "%");
    return '<svg class="donut" width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '" aria-hidden="true">' +
      '<circle cx="' + c + '" cy="' + c + '" r="' + r + '" fill="none" stroke="var(--line)" stroke-width="' + sw + '"/>' +
      '<circle cx="' + c + '" cy="' + c + '" r="' + r + '" fill="none" stroke="' + col + '" stroke-width="' + sw + '" ' +
      'stroke-linecap="round" stroke-dasharray="' + dash.toFixed(1) + ' ' + (circ - dash).toFixed(1) + '" transform="rotate(-90 ' + c + ' ' + c + ')"/>' +
      '<text x="' + c + '" y="' + c + '" text-anchor="middle" dominant-baseline="central" class="donut__t">' + esc(txt) + '</text>' +
      '</svg>';
  }
  // % medio de consecución sobre todos los parámetros con objetivo (real/obj)
  function achievedPct(p) {
    var acc = 0, n = 0;
    METRICS.forEach(function (mm) {
      var c = p[mm.key];
      if (c && c.obj && c.real != null) { acc += c.real / c.obj; n++; }
    });
    return n ? acc / n * 100 : null;
  }
  function playerDonut(p, match) {
    if (p.estado) return estadoTag(p.estado);
    if (match) return '<span class="pdet__sum">' + (p.playerLoad != null ? "PL " + fmt(p.playerLoad) : "—") + '</span>';
    var pc = achievedPct(p);
    if (pc == null) return '<span class="pdet__sum">—</span>';
    return donut(pc, semaphore(pc, 100));
  }

  /* ------------------------- componente métrica (fila) --------------------- */
  function objBar(meW, objL, sem) {
    if (objL == null) return "";
    var lo = Math.max(0, objL * 0.9).toFixed(1), hi = Math.min(100, objL * 1.1).toFixed(1);
    return '<div class="obar" style="--me:' + meW.toFixed(1) + '%;--obj:' + objL.toFixed(1) + '%;--lo:' + lo + '%;--hi:' + hi + '%">' +
      '<div class="obar__track"><span class="obar__zone"></span><span class="obar__fill ' + (sem || "") + '"></span></div>' +
      '<span class="obar__obj"></span><span class="obar__end ' + (sem || "") + '"></span></div>';
  }
  // fila de métrica: valor principal / objetivo / referencia (equipo o jugador)
  function mrow(label, unit, me, obj, ref, refLabel, dec) {
    var sem = semaphore(me, obj);
    var scale = Math.max(me || 0, obj || 0, ref || 0) * 1.12 || 1;
    var meW = me != null ? Math.max(2, Math.min(100, me / scale * 100)) : 0;
    var objL = obj != null ? Math.max(0, Math.min(100, obj / scale * 100)) : null;
    var f = dec ? function (v) { return fmtDec(v, dec); } : fmt;
    var cmpObj = obj != null ? '<span>obj <b>' + signed(pct(me, obj)) + '</b></span>' : "";
    var cmpRef = ref != null ? '<span>' + esc(refLabel || "equipo") + ' <b>' + signed(pct(me, ref)) + '</b></span>' : "";
    return '<div class="mrow">' +
      '<div class="mrow__head"><span class="mrow__label">' + esc(label) + (unit ? '<span class="mrow__unit">' + esc(unit) + '</span>' : '') + '</span>' +
      '<span class="mrow__cmp">' + cmpObj + (cmpObj && cmpRef ? ' · ' : '') + cmpRef + '</span></div>' +
      '<div class="mrow__vals">' +
      '<div class="mv mv--me"><span class="mv__n ' + (sem || "") + '">' + (me != null ? f(me) : "—") + '</span><span class="mv__k">real</span></div>' +
      '<div class="mv"><span class="mv__n">' + (obj != null ? f(obj) : "—") + '</span><span class="mv__k">objetivo</span></div>' +
      '<div class="mv mv--team"><span class="mv__n">' + (ref != null ? f(ref) : "—") + '</span><span class="mv__k">' + esc(refLabel || "media equipo") + '</span></div>' +
      '</div>' +
      objBar(meW, objL, sem) +
      '</div>';
  }

  /* --------------------- desplegable de jugador ---------------------- */
  function playerDetails(dorsal, name, grupo, summary, body, open) {
    return '<details class="pdet"' + (open ? ' open' : '') + '>' +
      '<summary>' + avatar(dorsal, name, "avatar--sm") +
      '<span class="pdet__name">' + esc(name) + '</span>' +
      '<span class="pdet__sum">' + summary + '</span>' +
      '<span class="pdet__chev">▾</span></summary>' +
      '<div class="pdet__body">' + body + '</div></details>';
  }
  function shareLine(dorsal, name) {
    var plink = "jugador.html?j=" + dorsal;
    return '<div class="pdet__share"><a class="btn btn--ghost" href="' + plink + '" target="_blank" rel="noopener">Vista del jugador</a>' +
      '<button class="btn btn--ghost" data-copylink="' + esc(plink) + '">Copiar enlace</button></div>';
  }

  /* ============================ INICIO ============================== */
  function screenInicio() {
    var m = currentMicro(), meta = m.meta || {};
    var keys = sessionKeys(m);
    var sesK = keys.filter(function (k) { return !isMatch(m, k); });
    var doneSes = sesK.filter(function (k) { return isCompleted(getSession(m, k)); });
    var lastKey = lastCompletedSessionKey(m);
    var last = getSession(m, lastKey);

    // avisos ACWR
    var av = m.cargaAC.players.filter(function (p) {
      return p.acwr === 0 || (p.acwr && (p.acwr < 0.80 || p.acwr > 1.30));
    }).sort(function (a, b) {
      var sa = a.acwr === 0 ? 99 : Math.abs(a.acwr - 1.05), sb = b.acwr === 0 ? 99 : Math.abs(b.acwr - 1.05);
      return sb - sa;
    });

    // cumplimiento equipo (distancia acumulada, solo sesiones)
    var co = m.cargasObjetivo.teamAvg.distancia;
    var cpct = co && co.obj ? Math.round(co.real / co.obj * 100) : null;

    // reparto semáforo última sesión + over/under
    var rep = { "sem-azul": 0, "sem-verde": 0, "sem-naranja": 0, "sem-rojo": 0 }, comp = 0, scored = [];
    if (!isMatch(m, lastKey)) last.players.forEach(function (p) {
      if (p.estado) return;
      var s = semaphore(p.distancia.real, p.distancia.obj);
      if (s) { rep[s]++; comp++; }
      var acc = 0, n = 0;
      METRICS.forEach(function (mm) { var c = p[mm.key]; if (c && c.obj) { acc += (c.real - c.obj) / c.obj; n++; } });
      if (n) scored.push({ dorsal: p.dorsal, name: p.jugador, score: acc / n });
    });
    scored.sort(function (a, b) { return b.score - a.score; });
    var over = scored.slice(0, 3).filter(function (x) { return x.score > 0.08; });
    var under = scored.slice(-3).reverse().filter(function (x) { return x.score < -0.08; });

    // ausencias en la última sesión
    var ausentes = isMatch(m, lastKey) ? [] : last.players.filter(function (p) { return p.estado === "na"; });

    /* ------------------------- avisos destacados ------------------------- */
    var flags = [];

    // récords de Vel. máx, agrupados por sesión/partido del microciclo
    var vBySes = {};
    keys.forEach(function (k) {
      var sk = getSession(m, k);
      if (!isCompleted(sk)) return;
      (sk.players || []).forEach(function (p) {
        if (p.estado || p.velMax == null) return;
        var prev = bestVelMax(p.dorsal, sk.date);
        if (prev && p.velMax > prev + 0.1) (vBySes[k] = vBySes[k] || []).push({ name: p.jugador, v: p.velMax, prev: prev });
      });
    });
    keys.forEach(function (k) {
      var arr = (vBySes[k] || []).sort(function (a, b) { return b.v - a.v; });
      if (!arr.length) return;
      if (arr.length === 1) {
        flags.push({ cls: "alert alert--ok", ico: iconOk(), goto: k,
          txt: "<b>" + esc(arr[0].name) + "</b> · récord de Vel. máx en " + k + ": <b>" + fmtDec(arr[0].v, 1) + "</b> km/h (antes " + fmtDec(arr[0].prev, 1) + ")" });
      } else {
        var names = arr.slice(0, 3).map(function (x) { return esc(x.name) + " " + fmtDec(x.v, 1); }).join(" · ");
        flags.push({ cls: "alert alert--ok", ico: iconOk(), goto: k,
          txt: "<b>" + arr.length + " récords de Vel. máx</b> en " + k + " · " + names + (arr.length > 3 ? " +" + (arr.length - 3) : "") });
      }
    });

    // ±50% respecto a lo previsto de media en la última sesión
    if (!isMatch(m, lastKey)) {
      var devs = [];
      last.players.forEach(function (p) {
        if (p.estado) return;
        var acc = 0, n = 0;
        METRICS.forEach(function (mm) { var c = p[mm.key]; if (c && c.obj && c.real != null) { acc += (c.real - c.obj) / c.obj; n++; } });
        if (n >= 3 && Math.abs(acc / n) >= 0.5) devs.push({ name: p.jugador, dv: acc / n });
      });
      devs.sort(function (a, b) { return Math.abs(b.dv) - Math.abs(a.dv); }).slice(0, 4).forEach(function (x) {
        flags.push(x.dv > 0
          ? { cls: "alert", ico: iconWarn(), goto: lastKey, txt: "<b>" + esc(x.name) + "</b> · <b>+" + Math.round(x.dv * 100) + "%</b> sobre lo previsto de media en " + lastKey + " — carga muy alta" }
          : { cls: "alert alert--info", ico: iconWarn(), goto: lastKey, txt: "<b>" + esc(x.name) + "</b> · <b>" + Math.round(x.dv * 100) + "%</b> respecto a lo previsto de media en " + lastKey + " — muy por debajo" });
      });
    }

    // se queda muy corto en el volumen del microciclo (solo con las sesiones ya completas)
    if (doneSes.length >= sesK.length - 1) {
      m.cargasObjetivo.players.map(function (p) {
        var c = p.distancia;
        return c && c.obj && c.real != null ? { name: p.jugador, r: c.real / c.obj } : null;
      }).filter(function (x) { return x && x.r < 0.55; })
        .sort(function (a, b) { return a.r - b.r; })
        .slice(0, 4)
        .forEach(function (x) {
          flags.push({ cls: "alert alert--info", ico: iconWarn(), goto: "micro",
            txt: "<b>" + esc(x.name) + "</b> · solo <b>" + Math.round(x.r * 100) + "%</b> del volumen de sesiones del microciclo" });
        });
    }

    var h = "";

    h += '<div class="card">' +
      '<div class="card__title">' + esc(meta.titulo || state.micro) + (meta.tipo ? ' · Tipo ' + esc(meta.tipo) : '') +
      (meta.estado === "activo" ? ' <span class="count">EN CURSO</span>' : '') + '</div>' +
      '<div class="muted">' + esc(meta.semana || "") + ' · último cálculo <b>' + esc(meta.calculoFecha || "—") + '</b></div>' +
      '<div class="kpi-row" style="margin-top:12px">' +
      kpi(doneSes.length + "/" + sesK.length, "Sesiones cargadas") +
      kpi(av.length, "Avisos de carga") +
      kpi(cpct != null ? cpct + "%" : "—", "Objetivo de sesiones", "distancia equipo") +
      kpi((rep["sem-naranja"] + rep["sem-rojo"]) + "/" + comp, "Pasados · " + lastKey) +
      '</div></div>';

    // avisos destacados
    if (flags.length) {
      h += '<div class="card"><div class="card__title">Avisos destacados <span class="count">' + flags.length + '</span></div>';
      h += flags.map(function (f) {
        return '<div class="' + f.cls + '"' + (f.goto ? ' data-goto="' + (f.goto === "micro" || f.goto === "cargaac" ? f.goto : "sesion") + '"' + (f.goto !== "micro" && f.goto !== "cargaac" ? ' data-session="' + f.goto + '"' : '') + ' style="cursor:pointer;margin-bottom:8px"' : ' style="margin-bottom:8px"') + '>' +
          f.ico + '<div>' + f.txt + '</div></div>';
      }).join("") + '</div>';
    }

    // avisos de carga
    h += '<div class="card"><div class="card__title">Avisos de carga (ACWR)</div>';
    if (!av.length) h += '<div class="alert alert--ok">' + iconOk() + '<div>Toda la plantilla dentro de zona (0,80–1,30).</div></div>';
    else h += av.map(function (p) {
      var cls = (p.acwr === 0 || p.acwr > 1.50) ? "alert" : p.acwr > 1.30 ? "alert alert--ok" : "alert alert--info";
      var msg = p.acwr === 0 ? "ACWR 0,00 — sin Player Load en 7 días. Revisar reintroducción."
        : p.acwr > 1.50 ? "ACWR " + fmtDec(p.acwr, 2) + " — riesgo de sobrecarga (>1,50)."
        : p.acwr > 1.30 ? "ACWR " + fmtDec(p.acwr, 2) + " — precaución (1,31–1,50)."
        : "ACWR " + fmtDec(p.acwr, 2) + " — infracarga (<0,80).";
      return '<div class="' + cls + '" data-goto="cargaac" style="margin-bottom:8px;cursor:pointer">' + iconWarn() +
        '<div><b>' + esc(p.jugador) + '</b> · ' + msg + '</div></div>';
    }).join("");
    h += '</div>';

    // última sesión
    h += '<div class="card"><div class="card__title">Última sesión <span class="count">' + lastKey + " · " + esc(roleShort(sessionRole(last))) + '</span></div>' +
      '<div class="muted" style="margin-bottom:10px">' + esc(fdate(last.date)) + '</div>' +
      '<div class="legend" style="margin-bottom:10px">' +
      '<span><i class="dot azul"></i>' + rep["sem-azul"] + ' cortos</span>' +
      '<span><i class="dot verde"></i>' + rep["sem-verde"] + ' cumplen</span>' +
      '<span><i class="dot naranja"></i>' + rep["sem-naranja"] + ' pasados</span>' +
      '<span><i class="dot rojo"></i>' + rep["sem-rojo"] + ' muy pasados</span></div>';
    if (over.length) h += '<div class="section-label">Se pasaron</div><div class="mini-list">' +
      over.map(function (x) { return miniP(x.dorsal, x.name, "+" + Math.round(x.score * 100) + "%"); }).join("") + '</div>';
    if (under.length) h += '<div class="section-label" style="margin-top:8px">Se quedaron cortos</div><div class="mini-list">' +
      under.map(function (x) { return miniP(x.dorsal, x.name, Math.round(x.score * 100) + "%"); }).join("") + '</div>';
    if (ausentes.length) h += '<div class="muted" style="font-size:12px;margin-top:10px">Sin datos: ' +
      ausentes.map(function (p) { return esc(p.jugador); }).join(" · ") + '</div>';
    h += '<button class="btn btn--primary" data-goto="sesion" data-session="' + lastKey + '" style="margin-top:12px">Ver la sesión</button></div>';

    // Top 5 por parámetro
    var plWeek = {};
    m.cargaAC.players.forEach(function (p) {
      var t = 0, any = false;
      Object.keys(p).forEach(function (k) { if (/^pl(S|PT)\d/.test(k) && p[k] != null) { t += p[k]; any = true; } });
      if (any) plWeek[p.dorsal] = t;
    });
    var pMet = METRICS.map(function (mm) {
      return { label: mm.label, unit: mm.unit, dec: 0, get: function (p) { return p[mm.key] && p[mm.key].real; } };
    });
    var sesParams = pMet.concat([
      { label: "Vel. máx", unit: "km/h", dec: 1, get: function (p) { return p.velMax; } },
      { label: "Player Load", unit: "", dec: 0, get: function (p) { return p.playerLoad; } }
    ]);
    var microParams = pMet.concat([
      { label: "Player Load", unit: "semana", dec: 0, get: function (p) { return plWeek[p.dorsal]; } }
    ]);

    if (!isMatch(m, lastKey)) h += '<div class="card"><div class="card__title">Top 5 · última sesión <span class="count">' + lastKey + '</span></div>' +
      '<div class="top5-grid">' + sesParams.map(function (pr) { return top5Card(pr, last.players); }).join("") + '</div></div>';

    h += '<div class="card"><div class="card__title">Top 5 · microciclo <span class="count">acumulado</span></div>' +
      '<div class="top5-grid">' + microParams.map(function (pr) { return top5Card(pr, m.cargasObjetivo.players); }).join("") + '</div></div>';

    return h;
  }
  function miniP(dorsal, name, badge) {
    return '<div class="mini-p">' + avatar(dorsal, name, "avatar--sm") +
      '<span>' + esc(name) + '</span><span class="mini-p__b">' + esc(badge) + '</span></div>';
  }
  function top5Card(pr, players) {
    var f = pr.dec ? function (v) { return fmtDec(v, pr.dec); } : fmt;
    var rows = players.map(function (p) { return { name: p.jugador, v: pr.get(p), estado: p.estado }; })
      .filter(function (x) { return !x.estado && x.v != null; })
      .sort(function (a, b) { return b.v - a.v; })
      .slice(0, 5);
    return '<div class="top5"><div class="top5__k">' + esc(pr.label) +
      (pr.unit ? ' <span class="top5__u">' + esc(pr.unit) + '</span>' : '') + '</div><ol class="top5__list">' +
      rows.map(function (x, i) {
        return '<li><b>' + (i + 1) + '</b><span>' + esc(x.name) + '</span><em>' + f(x.v) + '</em></li>';
      }).join("") + '</ol></div>';
  }
  // mejor Vel. máx del jugador en todo lo anterior a una fecha (sesiones y partidos)
  function bestVelMax(dorsal, beforeISO) {
    var best = 0;
    MICROS.forEach(function (mk) {
      sessionKeys(DATA[mk]).forEach(function (k) {
        var s = getSession(DATA[mk], k);
        if (!s.date || (beforeISO && s.date >= beforeISO)) return;
        var pp = (s.players || []).find(function (x) { return x.dorsal === dorsal; });
        if (pp && pp.velMax != null) best = Math.max(best, pp.velMax);
      });
    });
    return best;
  }

  /* ==================== SESIÓN / MICROCICLO ======================== */
  function teamMetricCards(ta, dec) {
    return '<div class="tm-grid">' + METRICS.map(function (mm) {
      var c = ta[mm.key] || {};
      var sem = c.obj != null ? semaphore(c.real, c.obj) : null;
      var f = fmt;
      return '<div class="tm">' +
        '<div class="tm__k">' + esc(mm.label) + ' <span class="mrow__unit">' + (mm.unit || "") + '</span></div>' +
        '<div class="tm__v"><span class="tm__real ' + (sem || "") + '">' + f(c.real) + '</span>' +
        '<span class="tm__obj">obj ' + f(c.obj) + (c.dif != null ? ' · ' + (c.dif > 0 ? "+" : "") + f(c.dif) : '') + '</span></div>' +
        '</div>';
    }).join("") + '</div>';
  }

  function screenSesion() {
    var m = currentMicro();
    var keys = sessionKeys(m);
    if (!state.session || keys.indexOf(state.session) < 0) state.session = lastCompletedSessionKey(m);
    var s = getSession(m, state.session);
    var match = isMatch(m, state.session);
    var done = isCompleted(s);
    var ta = s.teamAvg || {};

    var pills = '<div class="pills">' + keys.map(function (k) {
      var ss = getSession(m, k), mt = isMatch(m, k);
      return '<button class="pill' + (k === state.session ? " is-active" : "") + (isCompleted(ss) ? "" : " is-pending") +
        (mt ? " is-match" : "") + '" data-session="' + k + '">' + k +
        '<small>' + esc(mt ? ("vs " + (ss.rival || "Partido")).slice(0, 15) : roleShort(sessionRole(ss))) + '</small></button>';
    }).join("") + '</div>';

    var head = '<div class="card"><div class="card__title">Media del equipo <span class="count">' +
      state.session + ' · ' + esc(match ? ('vs ' + (s.rival || '—')) : roleShort(sessionRole(s))) + ' · ' + esc(fdate(s.date)) + '</span></div>';
    if (!done) head += '<div class="muted" style="margin-bottom:10px">' + (match ? 'Partido previsto, sin datos.' : 'Sesión prevista: solo objetivos.') + '</div>';
    else if (match) head += '<div class="muted" style="margin-bottom:10px">Un partido no lleva objetivo.</div>';

    var teamBody = done
      ? teamMetricCards(ta) +
        '<div class="info-metrics" style="margin-top:10px">' +
        kpi(ta.velMax != null ? fmtDec(ta.velMax, 1) : "—", "Vel. máx km/h") +
        kpi(fmt(ta.playerLoad), "Player Load") +
        kpi(ta.duracion || "—", "Duración") + '</div>'
      : '<div class="muted">—</div>';

    // jugadores
    var players = s.players.slice().sort(sortPlayers);
    var rows = players.map(function (p) {
      var sm = playerDonut(p, match);
      var body = "";
      if (p.estado === "na") body = '<div class="muted">Sin datos en esta sesión.</div>';
      else {
        body = METRICS.map(function (mm) {
          var c = p[mm.key] || {};
          var tr = (ta[mm.key] || {}).real;
          return mrow(mm.label, mm.unit, c.real, (match ? null : c.obj), tr, "media equipo", 0);
        }).join("");
        body += '<div class="info-metrics" style="margin-top:9px">' +
          kpi(p.velMax != null ? fmtDec(p.velMax, 1) : "—", "Vel. máx km/h") +
          kpi(fmt(p.playerLoad), "Player Load") +
          kpi(p.duracion || "—", "Duración") + '</div>';
      }
      body += shareLine(p.dorsal, p.jugador);
      return playerDetails(p.dorsal, p.jugador, p.grupo, sm, body);
    }).join("");

    return pills + head + teamBody + '</div>' +
      '<div class="card"><div class="card__title">Jugadores <span class="count">' + players.length + '</span></div>' +
      '<div class="pdet-list">' + rows + '</div></div>' +
      (s.nota ? '<div class="note">' + noteHtml(s.nota) + '</div>' : '');
  }

  function screenMicro() {
    var m = currentMicro();
    var co = m.cargasObjetivo;
    var ta = co.teamAvg;
    var sesK = sessionKeys(m).filter(function (k) { return !isMatch(m, k); });
    var pend = sesK.filter(function (k) { return !isCompleted(getSession(m, k)); });

    var head = '<div class="card"><div class="card__title">Media del equipo <span class="count">acumulado · ' + sesK.length + ' sesiones</span></div>' +
      '<div class="muted" style="margin-bottom:10px">Objetivo acumulado de las sesiones de entrenamiento (sin el partido).' +
      (pend.length ? ' Faltan: <b>' + esc(pend.join(" · ")) + '</b>.' : ' Sesiones completas.') + '</div>' +
      teamMetricCards(ta);

    var players = co.players.slice().sort(sortPlayers);
    var rows = players.map(function (p) {
      var body = METRICS.map(function (mm) {
        var c = p[mm.key] || {};
        return mrow(mm.label, mm.unit, c.real, c.obj, (ta[mm.key] || {}).real, "media equipo", 0);
      }).join("") + shareLine(p.dorsal, p.jugador);
      return playerDetails(p.dorsal, p.jugador, p.grupo, playerDonut(p, false), body);
    }).join("");

    return head + '</div>' +
      '<div class="card"><div class="card__title">Jugadores <span class="count">' + players.length + '</span></div>' +
      '<div class="pdet-list">' + rows + '</div></div>' +
      (co.nota ? '<div class="note">' + noteHtml(co.nota) + '</div>' : '');
  }

  /* ========================= CARGA A:C ============================= */
  function screenCargaAC() {
    var m = currentMicro();
    var ac = m.cargaAC;
    var ta = ac.teamAvg || {};
    var curSes = {}; sessionKeys(m).forEach(function (k) { curSes[k] = 1; });

    var teamCard = '<div class="card"><div class="card__title">Carga aguda·crónica del equipo</div>' +
      '<div class="stat-hero"><div class="stat-hero__num">' + fmtDec(ta.acwr, 2) + '</div>' +
      '<div class="stat-hero__label">ACWR medio · zona óptima 0,80–1,30</div></div>' +
      '<div class="kpi-row" style="margin-top:12px">' +
      kpi(fmt(ta.cargaAguda), "Carga aguda · media 7 d") +
      kpi(fmt(ta.cargaCronica), "Carga crónica · media 28 d") + '</div>' +
      (ac.serieTeam && ac.serieDias
        ? '<div class="section-label" style="margin:16px 0 2px">Últimos 28 días · media del equipo</div>' + acwrChart(ac.serieTeam, ac.serieDias, curSes)
        : "") +
      '</div>';

    var players = ac.players.slice().sort(sortPlayers);
    var rows = players.map(function (p) {
      var pk = Object.keys(p).filter(function (k) { return /^pl(S|PT)\d+/.test(k); });
      var pairs = pk.map(function (k) { return { label: k.slice(2), value: p[k] }; });
      var body = '<div class="grouprow" style="align-items:center;gap:12px;margin-bottom:8px">' +
        '<span class="acwr ' + acwrClass(p.acwr) + '" style="font-size:17px">' + fmtDec(p.acwr, 2) + '</span>' +
        '<span class="muted">Aguda <b>' + fmt(p.cargaAguda) + '</b> · Crónica <b>' + fmt(p.cargaCronica) + '</b> · equipo ' + fmtDec(ta.acwr, 2) + '</span></div>' +
        (p.serie && ac.serieDias ? acwrChart(p.serie, ac.serieDias, curSes) : trendBars(pairs)) +
        shareLine(p.dorsal, p.jugador);
      var sm = '<span class="acwr ' + acwrClass(p.acwr) + '">' + fmtDec(p.acwr, 2) + '</span>';
      return playerDetails(p.dorsal, p.jugador, p.grupo, sm, body);
    }).join("");

    return teamCard +
      '<div class="card"><div class="card__title">Jugadores <span class="count">' + players.length + '</span></div>' +
      '<div class="pdet-list">' + rows + '</div></div>' +
      '<div class="note">' + noteHtml(ac.nota) + '</div>';
  }

  function trendBars(pairs) {
    var vals = pairs.map(function (p) { return p.value; }).filter(function (v) { return v != null; });
    if (!vals.length) return '<div class="muted" style="padding:8px 0">Sin Player Load.</div>';
    var max = Math.max.apply(null, vals);
    return '<div class="trend-bars">' + pairs.map(function (p) {
      if (p.value == null) return '<div class="b" style="height:3px;background:var(--line)"><em>' + esc(p.label) + '</em></div>';
      var hh = Math.max(6, Math.round((p.value / max) * 92));
      return '<div class="b" style="height:' + hh + 'px"><span>' + fmt(p.value) + '</span><em>' + esc(p.label) + '</em></div>';
    }).join("") + '</div>';
  }

  function acwrChart(serie, dias, curSes) {
    curSes = curSes || {};
    var n = serie.pl.length;
    var padL = 30, padR = 10, colW = 14;
    var W = padL + n * colW + padR;
    var mT = 14, mH = 118, sGap = 26, sH = 82;
    var sT = mT + mH + sGap, H = sT + sH + 24;
    var cx = function (i) { return padL + colW * (i + 0.5); };
    var maxY = Math.max(50, Math.ceil((Math.max.apply(null, serie.pl.concat(serie.aguda, serie.cronica)) || 1) * 1.08 / 50) * 50);
    var my = function (v) { return mT + mH - (v / maxY) * mH; };
    var accv = serie.acwr.filter(function (v) { return v > 0; });
    var aLo = accv.length ? Math.min.apply(null, accv) : 0.8;
    var aHi = accv.length ? Math.max.apply(null, accv) : 1.3;
    var minA = Math.max(0, Math.min(aLo - 0.12, 0.74));
    var maxA = Math.min(2.8, Math.max(aHi + 0.12, 1.36));
    var sy = function (v) { v = Math.max(minA, Math.min(maxA, v)); return sT + sH - ((v - minA) / (maxA - minA)) * sH; };
    function path(a, f) { return a.map(function (v, i) { return (i ? "L" : "M") + cx(i).toFixed(1) + " " + f(v).toFixed(1); }).join(" "); }
    var bars = serie.pl.map(function (v, i) {
      if (!v) return "";
      return '<rect x="' + (cx(i) - colW * 0.31).toFixed(1) + '" y="' + my(v).toFixed(1) + '" width="' + (colW * 0.62).toFixed(1) +
        '" height="' + (mT + mH - my(v)).toFixed(1) + '" rx="1.5" style="fill:var(--azul);opacity:.5"/>';
    }).join("");
    var band = '<rect x="' + padL + '" y="' + sy(1.3).toFixed(1) + '" width="' + (n * colW) + '" height="' + (sy(0.8) - sy(1.3)).toFixed(1) + '" style="fill:var(--sem-verde-bg)"/>';
    var ref1 = '<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + sy(1).toFixed(1) + '" y2="' + sy(1).toFixed(1) + '" style="stroke:var(--neutro);stroke-dasharray:3 3"/>';
    var axes = '<line x1="' + padL + '" x2="' + padL + '" y1="' + mT + '" y2="' + (mT + mH) + '" style="stroke:var(--line)"/>' +
      '<line x1="' + padL + '" x2="' + (W - padR) + '" y1="' + (mT + mH) + '" y2="' + (mT + mH) + '" style="stroke:var(--line)"/>' +
      '<line x1="' + padL + '" x2="' + padL + '" y1="' + sT + '" y2="' + (sT + sH) + '" style="stroke:var(--line)"/>';
    var yl = '<text class="ax-v" x="' + (padL - 4) + '" y="' + (mT + 4) + '" text-anchor="end">' + fmt(maxY) + '</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (mT + mH) + '" text-anchor="end">0</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (sy(1.3) + 3).toFixed(1) + '" text-anchor="end">1,3</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (sy(1.0) + 3).toFixed(1) + '" text-anchor="end">1,0</text>' +
      '<text class="ax-v" x="' + (padL - 4) + '" y="' + (sy(0.8) + 3).toFixed(1) + '" text-anchor="end">0,8</text>';
    var xl = dias.map(function (iso, i) {
      var out = "";
      if (i % 7 === 0 || i === n - 1) out += '<text class="ax-v" x="' + cx(i).toFixed(1) + '" y="' + (H - 12) + '" text-anchor="middle">' + (+iso.slice(8)) + "/" + (+iso.slice(5, 7)) + '</text>';
      if (serie.ses[i]) out += '<line x1="' + cx(i).toFixed(1) + '" x2="' + cx(i).toFixed(1) + '" y1="' + mT + '" y2="' + (mT + mH) + '" style="stroke:var(--line);stroke-dasharray:2 2"/>';
      return out;
    }).join("");
    var curIdx = serie.ses.map(function (s, i) { return curSes[s] ? i : -1; }).filter(function (i) { return i >= 0; });
    var micBand = "";
    if (curIdx.length) {
      var a = cx(curIdx[0]) - colW * 0.5, b = cx(curIdx[curIdx.length - 1]) + colW * 0.5;
      micBand = '<rect x="' + a.toFixed(1) + '" y="' + mT + '" width="' + (b - a).toFixed(1) + '" height="' + mH + '" style="fill:var(--azul);opacity:.08"/>' +
        '<text class="ax-band" x="' + ((a + b) / 2).toFixed(1) + '" y="' + (mT + mH + 11) + '" text-anchor="middle">' + esc(state.micro) + '</text>';
    }
    var dac = serie.acwr.map(function (v, i) {
      var c = v === 0 ? "var(--neutro)" : v < 0.8 ? "var(--sem-azul)" : v > 1.5 ? "var(--sem-rojo)" : v > 1.3 ? "var(--sem-naranja)" : "var(--sem-verde)";
      return '<circle cx="' + cx(i).toFixed(1) + '" cy="' + sy(v).toFixed(1) + '" r="3.4" style="fill:' + c + '"/>';
    }).join("");
    return '<div style="margin:0 -6px">' +
      '<svg class="acwrc acwrc--w" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet" style="width:100%;display:block">' +
      micBand + band + ref1 + axes + bars +
      '<path d="' + path(serie.cronica, my) + '" style="fill:none;stroke:var(--oro);stroke-width:2.6;stroke-dasharray:5 3"/>' +
      '<path d="' + path(serie.aguda, my) + '" style="fill:none;stroke:var(--azul);stroke-width:2.8"/>' +
      '<path d="' + path(serie.acwr, sy) + '" style="fill:none;stroke:var(--txt-2);stroke-width:2.2"/>' +
      dac + yl + xl + '</svg></div>' +
      '<div class="radar-legend" style="flex-wrap:wrap;gap:8px 14px;margin-top:8px">' +
      '<span><b style="display:inline-block;width:10px;height:10px;background:var(--azul);border-radius:2px;vertical-align:middle;margin-right:6px"></b>Player Load</span>' +
      '<span><b style="display:inline-block;width:14px;border-top:3px solid var(--azul);vertical-align:middle;margin-right:6px"></b>Aguda 7 d</span>' +
      '<span><b style="display:inline-block;width:14px;border-top:3px dashed var(--oro);vertical-align:middle;margin-right:6px"></b>Crónica 28 d</span>' +
      '<span><b style="display:inline-block;width:10px;height:10px;background:var(--sem-verde-bg);border:1px solid var(--verde);border-radius:2px;vertical-align:middle;margin-right:6px"></b>ACWR · zona 0,80–1,30</span>' +
      '</div>';
  }

  /* ========================== PARTIDOS ============================= */
  function screenPartidos() {
    var t = DATA.refPartido.teamAvg || {};
    var sel = state.cmp.map(refPlayer).filter(Boolean);

    var series = [{ name: "Media equipo", color: "var(--oro)", dashed: true, vals: t }];
    sel.forEach(function (p, i) { series.push({ name: p.jugador, color: CMP_COLORS[i % CMP_COLORS.length], vals: p }); });

    var squad = DATA.refPartido.players || [];
    var axes = RADAR.map(function (mm) {
      var mx = 0;
      squad.forEach(function (p) { if (p[mm.key] != null && p[mm.key] > mx) mx = p[mm.key]; });
      return { key: mm.key, name: mm.short, label: mm.label, unit: mm.unit, dec: mm.dec || 0, team: t[mm.key], max: mx };
    }).filter(function (a) { return a.max > 0; });

    var chips = '<div class="cmp-chips">' + roster().map(function (p) {
      var on = state.cmp.indexOf(p.dorsal) >= 0;
      var ci = state.cmp.indexOf(p.dorsal);
      return '<button class="cmp-chip' + (on ? " is-on" : "") + '" data-cmp="' + p.dorsal + '"' +
        (on ? ' style="border-color:' + CMP_COLORS[ci % CMP_COLORS.length] + ';color:' + CMP_COLORS[ci % CMP_COLORS.length] + '"' : '') +
        '>#' + p.dorsal + ' ' + esc(p.jugador.split(",")[0]) + '</button>';
    }).join("") + '</div>';

    var lg = '<div class="radar-legend" style="flex-wrap:wrap">' + series.map(function (s) {
      return '<span><i style="border-color:' + s.color + (s.dashed ? ';border-top-style:dashed' : '') + '"></i>' + esc(s.name) + '</span>';
    }).join("") + '</div>';

    var table = "";
    if (sel.length) {
      table = '<div class="card"><div class="card__title">Comparativa <span class="count">REF_PARTIDO</span></div>' +
        '<div class="tablewrap"><table class="grid"><thead><tr><th class="col-player">Métrica</th><th>Equipo</th>' +
        sel.map(function (p) { return '<th>#' + p.dorsal + '</th>'; }).join("") + '</tr></thead><tbody>' +
        RADAR.map(function (mm) {
          var f = mm.dec ? function (v) { return fmtDec(v, mm.dec); } : fmt;
          return '<tr><td class="col-player">' + esc(mm.label) + ' <span class="obj">' + (mm.unit || "") + '</span></td>' +
            '<td class="num">' + f(t[mm.key]) + '</td>' +
            sel.map(function (p) {
              var pp = pct(p[mm.key], t[mm.key]);
              return '<td class="num">' + f(p[mm.key]) + ' <span class="obj">' + signed(pp) + '</span></td>';
            }).join("") + '</tr>';
        }).join("") + '</tbody></table></div></div>';
    }

    return '<div class="card"><div class="card__title">Perfil de partido</div>' +
      '<div class="muted" style="margin-bottom:10px">Telaraña de la media del equipo (REF_PARTIDO). Selecciona jugadores para superponer su perfil. El borde de la telaraña es el mejor registro de la plantilla en cada métrica.</div>' +
      chips +
      '<div class="radar-wrap" style="margin-top:8px">' + radarSVG(series, axes) + lg + '</div>' +
      (sel.length ? '<button class="btn btn--ghost" data-cmp-clear style="margin-top:8px">Quitar todos</button>' : '') +
      '</div>' + table +
      (DATA.refPartido.nota ? '<div class="note">' + noteHtml(DATA.refPartido.nota) + '</div>' : '');
  }

  function radarSVG(series, axes) {
    var N = axes.length, cx = 160, cy = 150, R = 100;
    function ang(i) { return -Math.PI / 2 + i * 2 * Math.PI / N; }
    function P(i, r) { return [(cx + r * Math.cos(ang(i))).toFixed(1), (cy + r * Math.sin(ang(i))).toFixed(1)]; }
    var rings = [0.25, 0.5, 0.75, 1].map(function (f) {
      return '<polygon class="grid-poly" points="' + axes.map(function (a, i) { return P(i, R * f).join(","); }).join(" ") + '"/>';
    }).join("");
    var spokes = axes.map(function (a, i) { var e = P(i, R); return '<line class="spoke" x1="' + cx + '" y1="' + cy + '" x2="' + e[0] + '" y2="' + e[1] + '"/>'; }).join("");
    var polys = series.map(function (s) {
      var pts = axes.map(function (a, i) {
        var v = s.vals[a.key];
        var r = (v == null || !a.max) ? 6 : Math.max(6, Math.min(R, R * (v / a.max)));
        return P(i, r).join(",");
      }).join(" ");
      var fill = s.dashed ? "none" : "color-mix(in srgb, " + s.color + " 16%, transparent)";
      return '<polygon points="' + pts + '" style="fill:' + fill + ';stroke:' + s.color + ';stroke-width:2.2;stroke-linejoin:round' +
        (s.dashed ? ';stroke-dasharray:5 4' : '') + '"/>';
    }).join("");
    var labels = axes.map(function (a, i) {
      var q = P(i, R + 15), x = +q[0], y = +q[1];
      var anchor = Math.abs(x - cx) < 8 ? "middle" : (x < cx ? "end" : "start");
      var f = a.dec ? fmtDec(a.max, a.dec) : fmt(a.max);
      return '<text class="ax-name" x="' + x + '" y="' + (y - 2) + '" text-anchor="' + anchor + '">' + esc(a.name) + '</text>' +
        '<text class="ax-val" x="' + x + '" y="' + (y + 9) + '" text-anchor="' + anchor + '">' + f + '</text>';
    }).join("");
    return '<svg class="radar" viewBox="0 0 320 300" role="img" aria-label="Telaraña de perfiles de partido">' +
      rings + spokes + polys + labels + '</svg>';
  }

  /* ------------------------- render: topbar ------------------------ */
  function renderTopbar() {
    var host = document.getElementById("microSelect");
    host.innerHTML = "";
    MICROS.forEach(function (k) {
      var mm = DATA[k].meta || {};
      host.appendChild(el('<button class="chip' + (k === state.micro ? " is-active" : "") + '" role="tab" data-micro="' + k + '">' +
        k + (mm.estado === "activo" ? '<span class="chip__tag">ACTIVO</span>' : '') + '</button>'));
    });
    var meta = currentMicro().meta || {};
    document.getElementById("microMeta").innerHTML =
      '<span><b>' + esc(meta.titulo || state.micro) + (meta.tipo ? ' · Tipo ' + esc(meta.tipo) : '') + '</b></span>' +
      '<span>' + esc(meta.semana || "") + '</span>' +
      '<span>Último cálculo <b>' + esc(meta.calculoFecha || "—") + '</b></span>';
    document.getElementById("topbarSub").textContent =
      ((DATA.meta && DATA.meta.club) ? DATA.meta.club + " · " : "") + "Preparación física";
  }

  /* ----------------------------- router --------------------------- */
  var SCREENS = { inicio: screenInicio, sesion: screenSesion, micro: screenMicro, cargaac: screenCargaAC, partidos: screenPartidos };
  function render() {
    renderTopbar();
    view.innerHTML = (SCREENS[state.screen] || screenInicio)();
    view.scrollTop = 0; window.scrollTo(0, 0);
    document.getElementById("microSelect").style.display = (state.screen === "partidos") ? "none" : "";
    Array.prototype.forEach.call(document.querySelectorAll(".navitem"), function (b) {
      b.classList.toggle("is-active", b.dataset.screen === state.screen);
    });
  }

  /* --------------------------- eventos ------------------------------- */
  document.getElementById("nav").addEventListener("click", function (e) {
    var b = e.target.closest(".navitem"); if (!b) return;
    state.screen = b.dataset.screen; render();
  });
  document.getElementById("microSelect").addEventListener("click", function (e) {
    var b = e.target.closest("[data-micro]"); if (!b) return;
    state.micro = b.dataset.micro; state.session = null; render();
  });
  view.addEventListener("click", function (e) {
    var copy = e.target.closest("[data-copylink]");
    if (copy) {
      var url = new URL(copy.dataset.copylink, location.href).href;
      var ok = function () { var t = copy.textContent; copy.textContent = "¡Copiado!"; setTimeout(function () { copy.textContent = t; }, 1500); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(ok, function () { window.prompt("Copia:", url); });
      else window.prompt("Copia:", url);
      return;
    }
    var goto = e.target.closest("[data-goto]");
    if (goto) { state.screen = goto.dataset.goto; if (goto.dataset.session) state.session = goto.dataset.session; render(); return; }
    var pill = e.target.closest(".pill[data-session]");
    if (pill) { state.session = pill.dataset.session; render(); return; }
    var cmp = e.target.closest("[data-cmp]");
    if (cmp) {
      var d = +cmp.dataset.cmp, i = state.cmp.indexOf(d);
      if (i >= 0) state.cmp.splice(i, 1);
      else if (state.cmp.length < CMP_COLORS.length) state.cmp.push(d);
      render(); return;
    }
    if (e.target.closest("[data-cmp-clear]")) { state.cmp = []; render(); return; }
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
  render();
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("sw.js").catch(function () {}); });
  }
})();
