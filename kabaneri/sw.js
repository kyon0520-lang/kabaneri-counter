// 旧URL（/kabaneri/）に残っているサービスワーカーを自分で片づけるためのファイル。
// ここを普通のリダイレクトにするとブラウザが更新を拒否して古い版が残り続けるので、
// 実体のあるJSとして置いておく必要がある。
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then(cs => cs.forEach(c => c.navigate('/kabaneri-unato/')))
  );
});
