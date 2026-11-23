// Guarda toda la guía en el teléfono la primera vez para que funcione sin internet.
const CACHE = "guia-candelaria-v1";
const ARCHIVOS = [
  "./", "index.html", "app.js", "manifest.webmanifest", "sitios_info.json",
  "modelo/modelo_web.onnx", "modelo/preproceso.json",
  "vendor/ort.min.js", "vendor/ort-wasm.wasm", "vendor/ort-wasm-simd.wasm",
  "img/hero.jpg", "img/catedral_primada.jpg", "img/capitolio.jpg", "img/plaza_bolivar.jpg",
  "img/palacio_lievano.jpg", "img/casa_narino.jpg", "img/san_francisco.jpg",
  "img/icono-192.png", "img/icono-512.png",
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ARCHIVOS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(r => r || fetch(e.request)));
});
