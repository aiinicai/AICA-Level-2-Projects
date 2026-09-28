/* LookThrough service worker.
   Makes the app installable and gives a clear page when the Data Bridge is not running.
   It caches ONLY the app shell below: an offline page, the icons and the manifest. It never caches the app page
   (which carries the portfolio data), the sign-in page or any /api response, so no client data is kept in the
   browser outside sign-in and the idle sign-out. Pages and data always come from the bridge. */
const CACHE = "lookthrough-shell-v1";
const SHELL = ["/offline.html", "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png", "/icons/icon-maskable-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;  // everything else goes straight to the network
  if (SHELL.includes(url.pathname)) {  // shell: cache first, so the offline page and icons are there when the bridge is not
    e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
    return;
  }
  if (req.mode === "navigate") {  // pages: always from the bridge, never stored; if it is not running, the offline page
    e.respondWith(fetch(req).catch(() => caches.match("/offline.html")));
  }
  // /api and anything else: network only, never cached
});
