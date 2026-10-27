/* Reglas comunes de cumplimiento (app entrenador, app jugador y dashboard).
   Mismo criterio que pipeline/config.py (TOLERANCIA y PESOS_DIA) — decisión del preparador, 27/10/2026.
   - Zona verde: Distancia y HMLD ±10%; HSR, ACC y DEC ±20%; Sprints ±2 en valor absoluto.
     Azul por debajo de la zona; naranja hasta el doble de la tolerancia por encima; rojo, más.
   - % de cumplimiento de una sesión = media ponderada de real/objetivo: en MD-4 ACC y DEC pesan
     doble; en MD-3, HSR y Sprints; Distancia y HMLD siempre peso 1. El de la semana = media de
     las sesiones. */
(function () {
  "use strict";
  var TOL = { distancia: ["pct", 10], hmld: ["pct", 10], hsr: ["pct", 20], acc: ["pct", 20], dec: ["pct", 20], sprint: ["abs", 2] };
  var PESOS = { "MD-4": { acc: 2, dec: 2 }, "MD-3": { hsr: 2, sprint: 2 } };
  var METR = ["distancia", "hmld", "hsr", "sprint", "acc", "dec"];
  function tol(m) { return TOL[m] || ["pct", 10]; }
  // "azul" | "verde" | "naranja" | "rojo" | null
  function zona(real, obj, m) {
    if (real == null || obj == null || obj === 0) return null;
    var t = tol(m), d = t[0] === "abs" ? real - obj : (real - obj) / obj * 100;
    if (d < -t[1]) return "azul";
    if (d <= t[1]) return "verde";
    if (d <= 2 * t[1]) return "naranja";
    return "rojo";
  }
  // zona verde en unidades de la métrica: [mín, máx]
  function banda(obj, m) {
    if (obj == null) return null;
    var t = tol(m);
    return t[0] === "abs" ? [Math.max(0, obj - t[1]), obj + t[1]] : [obj * (1 - t[1] / 100), obj * (1 + t[1] / 100)];
  }
  function dia(role) { return String(role || "").replace(/\s+/g, "").toUpperCase(); }
  function peso(role, m) { var p = PESOS[dia(role)]; return (p && p[m]) || 1; }
  // real/obj para el %; sprints: dentro de ±2 = 100%, fuera solo cuenta lo que se sale de la zona
  // (sobre un objetivo mínimo de 2). Igual que config.ratio_cumplimiento.
  function ratio(real, obj, m) {
    var t = tol(m);
    if (t[0] !== "abs") return real / obj;
    var d = real - obj;
    if (Math.abs(d) <= t[1]) return 1;
    return 1 + (d > 0 ? d - t[1] : d + t[1]) / Math.max(obj, t[1]);
  }
  // get(m) -> {obj, real}; devuelve % (100 = cumplido) o null
  function cumplimiento(get, role) {
    var a = 0, w = 0;
    METR.forEach(function (m) {
      var c = get(m);
      if (c && c.obj && c.real != null) { var k = peso(role, m); a += k * ratio(c.real, c.obj, m); w += k; }
    });
    return w ? a / w * 100 : null;
  }
  function textoTol(m) { var t = tol(m); return t[0] === "abs" ? "±" + t[1] : "±" + t[1] + "%"; }
  window.GPS_REGLAS = { TOL: TOL, PESOS: PESOS, zona: zona, banda: banda, peso: peso, ratio: ratio, cumplimiento: cumplimiento, textoTol: textoTol };
})();
