// Deckwright offline support. Bump VERSION whenever any app file changes.
const VERSION = "deckwright-v12";
const FONTS = "deckwright-fonts";
const SHELL = ["./", "index.html", "cards.js", "manifest.webmanifest",
  "qrcode.js", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => c.addAll(SHELL.map(u => new Request(u, { cache: "reload" }))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION && k !== FONTS).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (url.origin === location.origin) {
    if (req.mode === "navigate") {
      // newest page when online, cached page when offline
      e.respondWith(
        fetch(req)
          .then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put("index.html", copy)); return r; })
          .catch(() => caches.match("index.html"))
      );
      return;
    }
    if (/\/(cards\.js|combos\.json)$/.test(url.pathname)) {
      // data the weekly GitHub job refreshes: answer from the cache at once, fetch the newest copy for next time
      e.respondWith(caches.open(VERSION).then(async c => {
        const hit = await c.match(req, { ignoreSearch: true });
        const net = fetch(req, { cache: "no-cache" }).then(r => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => hit);
        return hit || net;
      }));
      return;
    }
    e.respondWith(caches.match(req, { ignoreSearch: true }).then(hit => hit || fetch(req)));
    return;
  }

  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    e.respondWith(caches.open(FONTS).then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      const r = await fetch(req);
      if (r.ok || r.type === "opaque") c.put(req, r.clone());
      return r;
    }));
  }
  // Anthropic and Scryfall requests go straight to the network.
});
