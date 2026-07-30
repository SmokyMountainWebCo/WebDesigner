# Internet Science — what actually happens between a keystroke and a pixel

> **Owns:** the mechanics. DNS resolution, connection setup, TLS, the HTTP
> protocol versions, caching layers, CDNs, and the browser's rendering
> path — plus the numbers that let you predict performance instead of
> guessing at it.
> **Not here:** getting found (`MASTERING-THE-INTERNET.md`). Making it
> look good (`DESIGN.md`). Pointing a real domain (`DNS-RUNBOOK.md`).

Most web performance advice is cargo cult because most people never learn
the sequence. Once you know the sequence, you can predict which change
will matter and skip the twelve that won't.

---

## The whole sequence, once

Someone types `example.com` and hits enter:

1. **DNS resolution** — the name becomes an IP address. Possibly zero
   network trips (cached in the browser, the OS, or the router); possibly
   four (recursive resolver → root → TLD → authoritative).
2. **TCP handshake** — SYN, SYN-ACK, ACK. One full round trip before a
   single byte of your content moves. (QUIC/HTTP3 folds this into the
   crypto handshake — see below.)
3. **TLS handshake** — certificate exchange and key agreement. One more
   round trip on TLS 1.3, two on 1.2.
4. **HTTP request** — finally. `GET / HTTP/1.1` plus headers.
5. **Server think time** — static file: microseconds. Database-backed
   page with no cache: anywhere from 20ms to several seconds.
6. **First bytes arrive** — the browser starts parsing HTML *immediately*,
   before the response finishes. This is why streaming HTML matters.
7. **Subresource discovery** — parser hits `<link>`, `<script>`, `<img>`.
   Each may need steps 1–5 again, unless same-origin (connection reused).
8. **Render** — style, layout, paint, composite. First paint, then
   incremental paints as more arrives.

**The load-bearing insight:** steps 1–4 are *latency* bound, not
bandwidth bound. On a connection with 60ms round-trip time, you have spent
~180ms before your server has even been asked for anything. Doubling
someone's bandwidth does nothing to that. Cutting a round trip does.

### Round trips are the currency

| Distance | Typical RTT | 4 round trips costs |
|---|---|---|
| Same city | 5–15 ms | 20–60 ms |
| Cross-country (US) | 60–80 ms | 240–320 ms |
| Transatlantic | 90–120 ms | 360–480 ms |
| Satellite (geostationary) | 500–600 ms | 2–2.4 s |
| Mobile, poor signal | 100–500 ms + jitter | up to 2 s |

Physics sets a floor: light in fiber travels roughly 200,000 km/s, and
routes are never straight. New York to London and back cannot beat ~56ms
no matter whose server it is. **This is the entire argument for CDNs** —
not bandwidth, just moving the endpoint closer so the round trips are
short.

---

## DNS, as a system

A hierarchical, aggressively cached, globally distributed key-value store.
Four layers of cache sit between a user and the authoritative answer:
browser, OS/stub resolver, recursive resolver (their ISP, or 1.1.1.1 /
8.8.8.8), and any intermediate. **TTL** (time to live, in seconds) tells
each layer how long it may keep an answer.

The consequence that bites people: **when you change a record, the old
answer stays live in caches for up to its previous TTL.** Lowering TTL
*after* the change does nothing — the caches already took the old value
with the old TTL. Lower it a day *before*. (Operational detail:
`DNS-RUNBOOK.md`.)

Record types worth knowing:

| Record | Maps | Note |
|---|---|---|
| `A` / `AAAA` | name → IPv4 / IPv6 | The literal address |
| `CNAME` | name → another name | Costs an extra lookup; illegal at the apex in classic DNS |
| `ALIAS`/`ANAME`/flattening | apex → another name | Provider-side workaround for the above |
| `MX` | domain → mail servers | Independent of the website. Break these, break the business |
| `TXT` | domain → arbitrary text | Verification, SPF, DKIM, DMARC |
| `CAA` | domain → allowed certificate issuers | Stops unauthorized certs being issued |
| `NS` | domain → authoritative nameservers | Set at the registrar |

**Anycast** is why `1.1.1.1` answers in 10ms worldwide: the same IP is
announced from hundreds of physical locations via BGP, and the network
routes you to the nearest. Modern DNS and CDNs both lean on it entirely.

**DNS is also a privacy leak** unless encrypted. DoH (DNS over HTTPS) and
DoT (DNS over TLS) fix the plaintext-query problem; neither hides the
destination IP or the TLS SNI field, so the network still learns which
site you visited unless Encrypted Client Hello is in play.

---

## TCP, TLS, and why HTTP/3 exists

**TCP** guarantees ordered, reliable delivery — and that guarantee is the
problem. A single lost packet stalls *everything* behind it in that
connection until the retransmission arrives (**head-of-line blocking**).
TCP also starts cautiously: **slow start** means the first response can
only be ~10 packets (~14 KB) before waiting for acknowledgement.

**That 14 KB number is actionable.** Content in the first ~14 KB of your
HTML response arrives one round trip sooner than content after it. Inline
your critical CSS and it renders in the first flight; link it as a
separate file and you pay a whole extra round trip before anything is
styled.

**TLS 1.3** cut the handshake from two round trips to one, and added
session resumption (0-RTT for repeat visitors, with replay caveats). Use
it; there is no reason to be on 1.2 in new deployments.

**HTTP versions, honestly:**

| Version | Multiplexing | Head-of-line blocking | Transport |
|---|---|---|---|
| HTTP/1.1 | No — 6 connections per origin, requests queue | Yes, per connection | TCP |
| HTTP/2 | Yes — many streams on one connection | At the TCP layer only | TCP |
| HTTP/3 | Yes | No — independent streams | QUIC over UDP |

HTTP/2 killed the old optimizations: **do not** concatenate every script
into one bundle, shard across `assets1.`/`assets2.` domains, or inline
sprites, purely for request-count reasons. Many small cacheable files now
beats one big one, because changing a byte of a bundle invalidates all of
it.

HTTP/3 (QUIC) merges transport and crypto setup into one handshake, moves
to UDP, survives network changes (wifi → cellular keeps the connection),
and eliminates transport-level head-of-line blocking. On lossy mobile
networks the difference is large; on a clean wired connection it is
marginal.

---

## Caching — the highest-leverage thing on this page

A request you never make costs nothing and cannot fail. The layers, in
order of how much they help:

1. **Browser cache** (disk/memory) — free, instant, zero network.
2. **CDN edge cache** — one short round trip, no origin involved.
3. **Reverse proxy / server cache** — skips application and database work.
4. **Application cache** (Redis, memcached) — skips the expensive query.
5. **Origin, doing the work** — what you're trying to avoid.

### The headers that matter

```
Cache-Control: public, max-age=31536000, immutable
```
For fingerprinted assets (`app.4f9a2c.css`). A year, never revalidated.
Safe *only* because the filename changes when the content does.

```
Cache-Control: no-cache
```
Badly named: it means "cache it, but revalidate before reuse." The
browser sends `If-None-Match`/`If-Modified-Since`, and the server can
answer `304 Not Modified` with no body. Correct default for HTML.

```
Cache-Control: no-store
```
Actually don't cache. For genuinely sensitive responses only.

```
Cache-Control: public, max-age=0, s-maxage=600, stale-while-revalidate=86400
```
The pattern worth memorizing for dynamic content: browsers always
revalidate, the CDN serves from edge for 10 minutes, and for a day after
that it serves stale instantly while refreshing in the background. Users
never wait for a cache miss.

**`ETag` vs `Last-Modified`:** an ETag is an opaque content fingerprint —
strong, works for generated content. `Last-Modified` has one-second
granularity and lies about files touched by deploys. Prefer ETag; ensure
it's derived from content, not from mtime or a per-server value, or your
load balancer will hand out mismatched tags and defeat revalidation.

**Cache invalidation is the hard part.** Two strategies actually work:
*fingerprint the filename* (content-addressed, invalidation is free), or
*keep TTLs short and purge explicitly* (an API call to the CDN on
deploy). Guessing at TTLs and hoping is the third strategy and it is why
people say "try a hard refresh."

### `Vary` is a footgun

`Vary: User-Agent` fragments your cache into thousands of near-duplicate
entries and effectively disables it. `Vary: Accept-Encoding` is normal and
fine. `Vary: Cookie` on HTML means every logged-in user gets their own
cache entry — sometimes correct, always expensive.

---

## CDNs

Two jobs, often conflated:

1. **Proximity** — terminate TLS and serve bytes from a POP near the
   user, which is the only way to beat round-trip physics.
2. **Offload** — absorb traffic so your origin does less.

They also give you, usually free: automatic TLS certificates, HTTP/3,
Brotli compression, image transcoding to WebP/AVIF, DDoS absorption, and
edge compute. For a static site this means the entire hosting problem is
solved by pushing to a git repository.

**Compression:** Brotli beats gzip by ~15–20% on text at comparable CPU
cost for static assets (pre-compress at build time at maximum quality).
Never compress already-compressed formats — JPEG, PNG, WebP, woff2, MP4
gain nothing and waste CPU. woff2 is *already* Brotli internally, which
is why it beats woff by ~30%.

---

## The browser rendering path

1. **HTML parse → DOM.** Incremental, as bytes arrive.
2. **CSS parse → CSSOM.** **Render-blocking**: nothing paints until the
   CSS that applies is parsed. This is by design — otherwise you'd see
   unstyled content flash.
3. **Scripts.** A plain `<script>` in `<head>` blocks parsing, because
   `document.write` might change the document. `defer` = fetch in
   parallel, execute after parsing, in order. `async` = fetch in
   parallel, execute whenever it lands, order not guaranteed. **`defer`
   is the right default.**
4. **Layout (reflow).** Compute geometry for every box. Expensive, and
   `O(elements)`.
5. **Paint.** Fill pixels, in layers.
6. **Composite.** Assemble layers — on the GPU, and this is the fast one.

### Why `transform` and `opacity` are the only cheap animations

They can be handled at the composite step alone. Everything else drags
layout or paint back into every frame:

| Animate this | Triggers | Result at 60fps |
|---|---|---|
| `transform`, `opacity`, `filter` | Composite | Cheap, GPU, smooth |
| `background-color`, `box-shadow`, `color` | Paint | Moderate |
| `width`, `height`, `top`, `left`, `margin`, `font-size` | **Layout** + paint | Jank |

You have **16.7 ms** per frame at 60Hz, and the browser needs part of it.
Assume ~10ms of budget for your own work.

**Layout thrashing** is the classic self-inflicted wound: read a geometry
property (`offsetHeight`, `getBoundingClientRect`), write a style, read
again — each read after a write forces a synchronous layout. Batch all
reads, then all writes.

**`content-visibility: auto`** lets the browser skip layout and paint
entirely for off-screen sections. On a long page it is close to a free
order-of-magnitude win on initial render. Pair with `contain-intrinsic-size`
so the scrollbar doesn't jump.

---

## Core Web Vitals, and what actually moves them

Google's field metrics, which also happen to be reasonable proxies for
"does this feel good."

**LCP — Largest Contentful Paint.** Good: ≤ 2.5s. When the biggest
element (usually a hero image or heading) paints. Fixes, in order of
typical impact:
- Don't lazy-load the LCP element. `loading="lazy"` on a hero image is a
  self-inflicted penalty. Use `fetchpriority="high"` instead.
- `<link rel="preload">` it, or better, put it in the HTML as a plain
  `<img>` the parser finds immediately.
- Serve it in AVIF/WebP at the size actually displayed.
- Cut render-blocking CSS; inline the critical part.
- If it's text, `font-display: swap` so it paints in a fallback rather
  than waiting.

**INP — Interaction to Next Paint.** Good: ≤ 200ms. Replaced FID in 2024
and is much harder to game: it measures the *worst* interaction latency,
not the first. Fixes:
- Break up long tasks. Anything over 50ms blocks the main thread.
- `await scheduler.yield()` (or a `setTimeout(0)` fallback) inside long
  loops so input can be handled between chunks.
- Move real computation to a Web Worker.
- Stop shipping hydration for content that was never interactive.

**CLS — Cumulative Layout Shift.** Good: ≤ 0.1. Content jumping while
someone reads. Almost entirely preventable:
- `width` and `height` attributes on every image and video, always. The
  browser reserves the box from the aspect ratio.
- Reserve space for ads, embeds, and banners before they load.
- Never insert content above existing content after paint.
- Use `size-adjust` / matched fallback metrics so the swap from fallback
  to web font doesn't reflow the page.

**Measure in the field, not just the lab.** Lighthouse on your own laptop
on office wifi is a synthetic test and it lies to you comfortably. Real
user monitoring — the `web-vitals` library posting to any endpoint, or
Chrome UX Report data — is what reflects the p75 your users actually get.

---

## Numbers worth memorizing

| Thing | Number |
|---|---|
| First TCP flight (slow start) | ~14 KB |
| Frame budget at 60Hz | 16.7 ms |
| "Long task" threshold | 50 ms |
| Feels instant | < 100 ms |
| Feels responsive, keeps flow | < 1 s |
| Attention starts to go | > 3 s |
| LCP / INP / CLS targets | 2.5 s / 200 ms / 0.1 |
| Typical 4G RTT | 50–100 ms |
| Cross-Atlantic RTT floor | ~56 ms |
| woff2 vs woff savings | ~30% |
| Brotli vs gzip on text | ~15–20% |
| AVIF vs JPEG at equal quality | ~50% smaller |

---

## Debugging, in the order that finds things fastest

1. **Network panel, "Disable cache" off and on.** Compare first visit to
   repeat visit. If they're the same, your caching is broken.
2. **Throttle to Slow 4G and 4× CPU.** Your machine is not the median
   device. This is the single most clarifying two-click change available.
3. **Performance panel recording.** Look for long tasks (red-cornered
   blocks) and layout events during animation.
4. **Coverage panel.** How much of your CSS and JS is unused on this
   page. The answer is usually humbling.
5. **`curl -sSv -o /dev/null https://example.com`** — see the real
   handshake, protocol version, and headers, with no browser cache or
   extension in the way.
6. **`dig +trace example.com`** — watch the full delegation chain when a
   name resolves oddly.
7. **WebPageTest, from a location that isn't yours.** Waterfall plus
   filmstrip tells you what a stranger experiences.

---

## Sources to check against, because this changes

- **MDN Web Docs** (`developer.mozilla.org`) — the reference. CC-BY-SA.
- **web.dev** — Google's platform guidance and the canonical Web Vitals
  definitions.
- **Can I Use** (`caniuse.com`) — support tables with real usage data.
- **HTTP Archive / Web Almanac** — what the top few million sites
  actually do, annually, with data.
- **The RFCs** — HTTP/1.1 is 9110–9112, HTTP/2 is 9113, HTTP/3 is 9114,
  QUIC is 9000, TLS 1.3 is 8446. Dry, and definitive.
- **High Performance Browser Networking**, Ilya Grigorik — free online,
  still the best single explanation of the transport layers.

*Numbers and thresholds above are current as of 2026-07. Vitals
thresholds and metric definitions have changed before (FID → INP) and
will again — re-check web.dev before quoting them.*
