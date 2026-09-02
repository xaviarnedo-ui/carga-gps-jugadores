/* Service worker — cache básico para uso offline en el campo + notificaciones push. */
var CACHE = "carga-gps-v41";
var ASSETS = [
  "./",
  "./index.html",
  "./jugador.html",
  "./styles.css?v=41",
  "./app.js?v=41",
  "./jugador.js?v=41",
  "./data.js?v=41",
  "./manifest.json",
  "./manifest.jugador.json",
  "./icons/escudo.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return Promise.all(ASSETS.map(function (u) { return c.add(u).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  // data.js siempre fresco si hay red (los datos cambian cada día)
  if (url.pathname.endsWith("/data.js")) {
    e.respondWith(
      fetch(e.request).then(function (r) {
        var copy = r.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return r;
      }).catch(function () { return caches.match(e.request); })
    );
    return;
  }
  e.respondWith(caches.match(e.request).then(function (r) { return r || fetch(e.request); }));
});

/* ---- Notificaciones push ---- */
self.addEventListener("push", function (e) {
  var p = { title: "Carga GPS", body: "Datos de GPS actualizados", url: "./jugador.html" };
  if (e.data) {
    try { var j = e.data.json(); p.title = j.title || p.title; p.body = j.body || p.body; p.url = j.url || p.url; }
    catch (x) { p.body = e.data.text(); }
  }
  e.waitUntil(self.registration.showNotification(p.title, {
    body: p.body,
    icon: "./icons/icon-192.png",
    badge: "./icons/icon-192.png",
    data: { url: p.url }
  }));
});

self.addEventListener("notificationclick", function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || "./jugador.html";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (cl) {
    for (var i = 0; i < cl.length; i++) {
      if ("focus" in cl[i]) { cl[i].navigate && cl[i].navigate(url); return cl[i].focus(); }
    }
    if (self.clients.openWindow) return self.clients.openWindow(url);
  }));
});
