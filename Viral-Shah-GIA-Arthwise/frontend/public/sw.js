const CACHE_NAME = 'giaarthwise-loan-app-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
];

// Install: Cache static shell assets only
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: NEVER cache API responses or uploaded documents (DPDP & Banking Security Requirement)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Strictly exclude API routes, reports, and uploaded documents
  if (url.pathname.startsWith('/api') || url.pathname.includes('/reports/') || url.pathname.includes('/documents/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Network first with cache fallback for static app shell
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
