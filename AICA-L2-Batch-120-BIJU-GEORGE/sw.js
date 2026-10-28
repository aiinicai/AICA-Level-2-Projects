/**
 * sw.js - Service Worker for CubeSolver PWA
 * Network-first strategy with cache fallback for 100% offline availability
 * and immediate real-time updates.
 */

const CACHE_NAME = 'cubesolver-pwa-v29';

const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.webmanifest',
    './css/styles.css',
    './js/lib/three.min.js',
    './js/lib/OrbitControls.js',
    './js/lib/cube.js',
    './js/lib/solve.js',
    './js/model/CubeState.js',
    './js/solver/KociembaSolver.js',
    './js/solver/LayerByLayerSolver.js',
    './js/ui/Cube3D.js',
    './js/ui/CubeVision.js',
    './js/ui/CameraScanner.js',
    './js/ui/ManualEditor.js',
    './js/ui/SolutionVisualizer.js',
    './js/ui/SolutionDiagram.js',
    './js/ui/NotationGuide.js',
    './js/ui/Timer.js',
    './js/ui/CubeAcademy.js',
    './js/ui/UserManual.js',
    './js/ui/AudioEffects.js',
    './js/app.js',
    './assets/icon-192.png',
    './assets/icon-512.png'
];

self.addEventListener('install', (event) => {
    // Immediately activate new service worker without waiting
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS_TO_CACHE).catch(err => {
                console.warn('Pre-cache warning:', err);
            });
        })
    );
});

self.addEventListener('activate', (event) => {
    // Clean up all obsolete caches
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => {
                    console.log('Purging legacy cache:', k);
                    return caches.delete(k);
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Network-First strategy: Always fetch fresh code from server if available;
// fallback to cache if offline.
self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request, { cache: 'no-cache' })
            .then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200) {
                    const responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                // Offline fallback
                return caches.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    if (event.request.destination === 'document') {
                        return caches.match('./index.html');
                    }
                });
            })
    );
});
