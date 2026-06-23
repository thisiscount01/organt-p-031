const CACHE = 'cineai-v2';
const SHELL = [
  '/',
  '/index.html',
  '/css/style.css',
  '/js/quiz-engine.js',
  '/js/store.js',
  '/js/pages.js',
  '/js/app.js',
  '/vendor/css/bootstrap.min.css',
  '/vendor/css/all.min.css',
  '/vendor/js/vue.global.prod.js',
  '/vendor/js/axios.min.js',
  '/vendor/js/bootstrap.bundle.min.js',
  // 정적 데이터: SW install 시 프리캐시 → 콜드스타트와 무관하게 즉시 로드
  '/data/movies.json',
  '/data/genres.json',
];

self.addEventListener('install', e =>
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()))
);
self.addEventListener('activate', e =>
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()))
);
// ── Keep-alive: SW가 서버를 깨워줌 (Render cold-start 방어) ──────────────
function keepAlive() {
  fetch('/api/health').catch(() => {});
  setTimeout(keepAlive, 28 * 60 * 1000); // 28분 간격 (SW 라이프사이클 내 주기적 ping)
}
self.addEventListener('activate', () => { keepAlive(); });

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // API·외부 요청은 네트워크 우선
  if (url.pathname.startsWith('/api/') || url.origin !== self.location.origin) return;
  // 앱 셸: 캐시 우선, 백그라운드 업데이트
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fresh = fetch(e.request).then(res => {
        if (res.ok) caches.open(CACHE).then(c => c.put(e.request, res.clone()));
        return res;
      });
      return cached || fresh;
    })
  );
});
