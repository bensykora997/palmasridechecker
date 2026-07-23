/* Palmas Ride Engine service worker.
 *
 * Strategy:
 *   - App shell (HTML/CSS/JS/icons/Leaflet): cache-first, so the app opens
 *     instantly and works offline.
 *   - /api/*: network-only and never cached here — predictions must be live.
 *     (app.js keeps its own last-good prediction in localStorage for the
 *     offline fallback banner.)
 *
 * Bump CACHE_VERSION whenever the shell assets change to evict the old cache.
 */
const CACHE_VERSION = "palmas-v3";
const SHELL = [
  "/",
  "/index.html",
  "/app.js",
  "/style.css",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/favicon.svg",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      // Don't fail the whole install if a CDN asset hiccups.
      Promise.allSettled(SHELL.map((url) => cache.add(url)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // API: always go to network, never serve a cached prediction.
  if (url.pathname.startsWith("/api/")) {
    return; // default browser fetch
  }

  // Shell: cache-first, fall back to network and populate the cache.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((resp) => {
        // Cache same-origin + the known CDN assets opportunistically.
        if (resp && resp.status === 200 && (url.origin === self.location.origin || url.host === "unpkg.com")) {
          const copy = resp.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(request, copy));
        }
        return resp;
      }).catch(() => cached);
    })
  );
});
