/* Service worker for the InternLink installable web app.
 *
 * Served from /sw.js so it controls the whole site.
 *
 * Strategy:
 *   - Navigations: network first, offline page as the fallback. Private HTML is
 *     never cached, so signing out cannot expose another user's pages.
 *   - Static assets: cache first, then network.
 *   - Everything else (POST, admin, media): untouched.
 */
const CACHE_VERSION = 'internlink-v2';
const OFFLINE_URL = '/offline/';
const PRECACHE_URLS = [
    OFFLINE_URL,
    '/static/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil((async () => {
        const cache = await caches.open(CACHE_VERSION);
        await Promise.all(
            PRECACHE_URLS.map((url) =>
                cache.add(new Request(url, { cache: 'reload' })).catch(() => null)
            )
        );
        await self.skipWaiting();
    })());
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        const keys = await caches.keys();
        await Promise.all(
            keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))
        );
        await self.clients.claim();
    })());
});

self.addEventListener('fetch', (event) => {
    const request = event.request;

    if (request.method !== 'GET') {
        return;
    }

    const url = new URL(request.url);
    if (url.origin !== self.location.origin) {
        return;
    }
    if (url.pathname.startsWith('/admin/') || url.pathname === '/sw.js') {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith((async () => {
            try {
                // no-store: never serve a cached login page. A stale page carries
                // an old CSRF token and the form then fails with 403.
                return await fetch(request, { cache: 'no-store' });
            } catch (error) {
                const cache = await caches.open(CACHE_VERSION);
                const offline = await cache.match(OFFLINE_URL);
                return offline || Response.error();
            }
        })());
        return;
    }

    if (url.pathname.startsWith('/static/')) {
        event.respondWith((async () => {
            const cache = await caches.open(CACHE_VERSION);
            const cached = await cache.match(request);
            if (cached) {
                return cached;
            }
            const response = await fetch(request);
            if (response.ok) {
                cache.put(request, response.clone());
            }
            return response;
        })());
    }
});
