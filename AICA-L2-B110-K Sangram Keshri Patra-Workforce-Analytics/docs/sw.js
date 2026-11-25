/* Offline support: app shell cached, data fetched fresh when online (falls back to last copy offline). */
const CACHE = 'wf-dashboard-v6';
const SHELL = ['./', 'index.html', 'styles.css', 'app.js', 'lib/d3.min.js', 'manifest.webmanifest',
  'icons/icon-192.png', 'icons/icon-512.png', 'icons/apple-touch-icon.png'];

self.addEventListener('install', (e) => e.waitUntil(caches.open(CACHE).then(async (c) => {
  await c.addAll(SHELL);
  try {   // also keep every month listed in data/index.json for offline use
    const ix = await fetch('data/index.json', { cache: 'no-cache' });
    const months = (await ix.clone().json()).periods || [];
    await c.put('data/index.json', ix);
    await c.addAll(months.map((p) => `data/dashboard_data_${p}.json`));
  } catch (err) { /* data is cached on first use instead */ }
}).then(() => self.skipWaiting())));
self.addEventListener('activate', (e) => e.waitUntil(
  caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.endsWith('.json') && url.pathname.includes('/data/')) {
    e.respondWith(fetch(e.request).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request, { ignoreSearch: true })));
    return;
  }
  // app files: network first so a new release shows at once; cached copy when offline
  e.respondWith(fetch(e.request).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request, { ignoreSearch: true })));
});
