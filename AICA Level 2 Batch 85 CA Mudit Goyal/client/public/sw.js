/**
 * MGSG Lite — Service Worker
 *
 *   App shell (HTML, JS, CSS) → cache-first, refreshed in the background
 *   API calls (/api/*)        → network-first, falling back to a recent cache
 *   Navigations               → network, then the cached shell, then /offline.html
 *
 * The point of the API fallback is the field case the attendance screen is
 * built for: a phone on a weak signal should still show the day it already
 * loaded rather than an error page.
 */

const CACHE_NAME = 'mgsg-lite-v1';
// A real file, not a clean URL — a host that rewrites /offline to /offline.html
// would serve the SPA shell here instead and the offline page would never show.
const OFFLINE_URL = '/offline.html';

const PRE_CACHE = ['/', '/offline.html', '/manifest.json'];

/** How stale a cached API response may be before it is no longer worth showing. */
const API_MAX_AGE_SECONDS = 5 * 60;

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRE_CACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))),
  );
  self.clients.claim();
});

// The update banner posts this when the user taps Refresh.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, clone));
          return response;
        })
        .catch(async () => (await caches.match('/')) || caches.match(OFFLINE_URL)),
    );
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) {
      const dateHeader = cached.headers.get('date');
      if (!dateHeader) return cached;
      const age = (Date.now() - new Date(dateHeader).getTime()) / 1000;
      if (age < API_MAX_AGE_SECONDS) return cached;
    }
    // A shaped response, so the app can say "you are offline" rather than
    // showing a parse error from an HTML error page.
    return new Response(JSON.stringify({ message: 'You are offline', offline: true }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetching = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);
  return cached || fetching;
}
