/* 최소 서비스워커: 오프라인 폴백 + 정적 자산 캐시.
   전략 변경 시 CACHE_VERSION을 올려야 기존 캐시가 교체된다. */

const CACHE_VERSION = "v1";
const CACHE_NAME = `kyongmapick-${CACHE_VERSION}`;
const PRECACHE_URLS = ["/offline", "/icon-192.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // 페이지 내비게이션: 네트워크 우선, 실패 시 오프라인 폴백
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches
          .match(request)
          .then((cached) => cached ?? caches.match("/offline")),
      ),
    );
    return;
  }

  // 해시가 붙은 빌드 자산: 캐시 우선 (불변)
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ??
          fetch(request).then((response) => {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
            return response;
          }),
      ),
    );
  }
});
