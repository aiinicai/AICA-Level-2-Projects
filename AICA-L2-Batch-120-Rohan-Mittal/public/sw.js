// Fair Share Service Worker — lightweight PWA service worker.
// Wipes any legacy Workbox caches on activation and never forces page reloads or caches auth redirects.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/__") ||
    url.pathname.startsWith("/_aistudio") ||
    url.pathname.startsWith("/node_modules/") ||
    url.pathname.startsWith("/@") ||
    url.searchParams.has("__aistudio_auth_token") ||
    url.searchParams.has("__storage_access_granted")
  ) {
    return;
  }
  // Network pass-through satisfies browser PWA installability requirements without serving stale HTML/auth redirects
});
