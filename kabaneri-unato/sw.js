// オフラインでも起動できるようにするサービスワーカー
// index.html を更新したら CACHE の数字を上げること（古いキャッシュが残るのを防ぐ）
const CACHE = 'kabaneri-counter-v103';

const ASSETS = [
  './',
  './index.html',
  './manual.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// まずネットワーク、だめならキャッシュ（ホールで圏外でも起動できる）
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);
  // APIと外部ドメインは素通しにする。
  // 貯めると、引き継ぎで受け取った記録の中身がキャッシュに残り続け、
  // 圏外のときに古い応答を返してしまう
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(e.request).then(hit => hit || caches.match('./index.html')))
  );
});
