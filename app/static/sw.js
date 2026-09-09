// Self-Clearing Service Worker for Minerals Oracle PWA (Purges legacy caches)
const CACHE_NAME = 'minerals-oracle-v2';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map((key) => caches.delete(key)));
    }).then(() => self.registration.unregister())
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Always fetch fresh from network, no caching
  event.respondWith(fetch(event.request));
});
