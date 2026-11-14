const CACHE_NAME = 'bullion-ledger-v2.3.0';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/Price%20History.csv'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Clearing old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim()).then(async () => {
      // Auto-cleanup for localhost development: unregister and reload windows
      try {
        const clients = await self.clients.matchAll({ type: 'window' });
        for (const client of clients) {
          const url = new URL(client.url);
          if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
            await self.registration.unregister();
            client.navigate(client.url);
          }
        }
      } catch (e) {
        // ignore
      }
    })
  );
});

self.addEventListener('fetch', (event) => {
  // Only cache GET requests
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);

  // NEVER cache localhost or Vite dev server requests inside SW
  if (url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.port === '3000') {
    return;
  }

  // Network first for HTML / app-shell, fallback to cache
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  // Cache first for static assets, network fallback
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return response;
      });
    }).catch(() => {
      // offline fallback
      return new Response('Offline: Content cached when online.', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: new Headers({ 'Content-Type': 'text/plain' })
      });
    })
  );
});
