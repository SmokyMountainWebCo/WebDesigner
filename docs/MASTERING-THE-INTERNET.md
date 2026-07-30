# Mastering the Internet — being found, being previewed, being measured

> **Owns:** distribution mechanics. How crawlers find and index a page,
> what structured data does, how a pasted link becomes a rich card, feeds
> and syndication, redirects and URL hygiene, and how to measure any of
> it.
> **Not here:** the transport and caching layers
> (`INTERNET-SCIENCE.md`). Visual craft (`DESIGN.md`).

Building the thing is half. The other half is that the internet is an
indexing machine, a preview machine, and a link graph — and all three have
documented, stable interfaces you can address directly. Most sites leave
them empty and then wonder why nothing happens.

---

## How a crawler actually sees your site

1. **Discovery.** A URL enters the queue from a link somewhere, a sitemap,
   a redirect, or a previous crawl.
2. **`robots.txt` check.** Fetched and cached (~24h). A `Disallow` here
   means *don't fetch* — which also means the crawler never sees your
   `noindex` tag. This is the classic mistake: to keep a page out of the
   index you must let it be *crawled* so the `noindex` is visible.
3. **Fetch.** Under a crawl budget: a rate the crawler infers from your
   server's speed and error rate. Slow, 5xx-prone servers get crawled
   less.
4. **Render.** Modern crawlers execute JavaScript, but in a second pass
   from a deferred queue, on an unpredictable delay, with no guarantee.
   Content in the initial HTML is indexed immediately and reliably;
   content that requires JS is indexed eventually and sometimes.
5. **Canonicalization.** Duplicates are clustered and one URL is chosen as
   canonical. Your `rel=canonical` is a *hint*, weighed against
   redirects, internal links, sitemaps, and consistency. Contradict
   yourself and the crawler decides for you.
6. **Index.** Or not. Being crawled is not being indexed; "Crawled —
   currently not indexed" means it was judged not worth storing.

**The one rule that follows from all of that:** put the content in the
HTML. Server-render, static-generate, or write it by hand — but let the
first response contain the words you want found.

### `robots.txt`

```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /*?sort=

Sitemap: https://example.com/sitemap.xml
```

It is a **crawl** directive, public, advisory, and honored by the
mainstream crawlers only. It is not access control — never list secret
paths in it; you are publishing a map of them.

`Crawl-delay` is ignored by Google. AI-crawler opt-outs are their own
mess: `GPTBot`, `ClaudeBot`, `CCBot`, `Google-Extended` and others are
per-agent tokens with no standard, so an opt-out is a list you maintain by
hand. Whether to opt out is a business decision, not a technical one.

### Indexing directives, per page

```html
<meta name="robots" content="noindex, nofollow">   <!-- keep out entirely -->
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="https://example.com/the-real-url">
```

`X-Robots-Tag` as an HTTP header does the same and works for non-HTML
(PDFs, images) where you can't put a meta tag.

**Unlisted ≠ private.** `noindex` plus no inbound links keeps a page out
of search results, and anyone with the URL can still open it. That's what
makes a shareable link work — and why nothing sensitive belongs on one.

### `sitemap.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page</loc>
    <lastmod>2026-07-30</lastmod>
  </url>
</urlset>
```

Only `<loc>` and `<lastmod>` are worth writing — `priority` and
`changefreq` are ignored by Google. `lastmod` is used, but only if it's
honest; sitemaps that claim every page changed today get their `lastmod`
discounted entirely. Include only canonical, indexable, 200-status URLs.
50,000 URLs or 50MB uncompressed per file, then split and use a sitemap
index.

---

## Structured data — the highest-leverage markup available

JSON-LD in a `<script>` tag tells machines what the page *is*, not just
what it says. It's the difference between a blue link and a result with a
star rating, a price, an address, and opening hours.

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "Example Studio",
  "url": "https://example.com",
  "telephone": "+1-555-0100",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "1 Main St",
    "addressLocality": "Anytown",
    "addressRegion": "TN",
    "postalCode": "37000",
    "addressCountry": "US"
  },
  "geo": { "@type": "GeoCoordinates", "latitude": 35.8, "longitude": -83.5 },
  "openingHoursSpecification": [{
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
    "opens": "09:00", "closes": "17:00"
  }],
  "sameAs": ["https://www.instagram.com/example"]
}
</script>
```

Types with actual documented search features behind them: `Article`,
`BreadcrumbList`, `FAQPage`, `HowTo`, `Product` (+`Offer`, `AggregateRating`),
`Recipe`, `Event`, `JobPosting`, `LocalBusiness`, `Organization`,
`Person`, `VideoObject`, `SoftwareApplication`, `Course`. The full
vocabulary at `schema.org` is much larger and mostly not rendered
specially — but it's still machine-readable, and increasingly it's what
language models read.

**Rules:** JSON-LD over microdata (separable from markup, easier to
maintain). Mark up only what a human can see on the page — invisible
structured data is a violation and gets manual actions. Validate with the
Schema Markup Validator and Google's Rich Results Test. `@id` with a
stable URL lets you link entities across pages into a graph.

**`BreadcrumbList` is the underrated one:** it replaces the ugly URL in
search results with a readable hierarchy, on every page, for ~15 lines of
markup.

---

## Link previews — one tag set, every platform

When a URL is pasted into Slack, iMessage, WhatsApp, LinkedIn, Discord, a
Facebook post, or a text message, a bot fetches it and reads Open Graph
tags. Get these wrong and your link is a bare grey rectangle; get them
right and it's a card.

```html
<meta property="og:title"       content="Under ~60 characters">
<meta property="og:description" content="Under ~155 characters.">
<meta property="og:image"       content="https://example.com/og.png">
<meta property="og:image:width"  content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt"   content="Described for screen readers">
<meta property="og:url"         content="https://example.com/page">
<meta property="og:type"        content="website">
<meta property="og:site_name"   content="Example">
<meta name="twitter:card"       content="summary_large_image">
```

**Specifics that matter:**
- **1200×630** (1.91:1) is the safe universal size. Under 200×200 gets
  ignored. Keep it under ~1MB; some scrapers give up.
- **Absolute URLs only.** Relative `og:image` paths fail on most
  scrapers.
- **Declare width and height.** Some platforms render the card
  immediately with the declared box and fetch the image after.
- **Crawlers don't run JavaScript.** OG tags injected client-side do not
  exist. They must be in the served HTML.
- **Previews are cached hard.** Fix a bad card and re-scrape it
  deliberately: Facebook's Sharing Debugger, LinkedIn's Post Inspector,
  X's card validator. Otherwise the wrong card persists for days.
- **Generate the image, don't design each one.** An HTML page rendered
  headlessly to PNG at 1200×630 gives you per-page cards for free — same
  fonts, same palette, one template. (Headless Chromium via Playwright;
  `tools/check.js` in this repo shows the screenshot mechanics.)

Also worth having: `<link rel="icon">` with an SVG plus a 180×180 PNG for
`apple-touch-icon`, and a `theme-color` meta so mobile browser chrome
matches the page.

---

## URL hygiene and redirects

URLs are a public API. Once someone bookmarks, links, or prints one,
changing it costs you.

**Design:** lowercase, hyphens not underscores, no file extensions, no
session IDs, shallow, readable, stable. `/guides/dns-basics` outlives
`/index.php?p=1187&cat=3`.

**Pick one canonical form and enforce it with 301s:** `https` not `http`,
one of `www` or bare, no trailing slash inconsistency. Every variant that
resolves independently splits your link equity and duplicates your crawl
budget.

| Status | Meaning | Use for |
|---|---|---|
| 301 | Moved permanently | Real moves. Cached hard by browsers — be sure |
| 308 | Permanent, method preserved | Same, but won't turn POST into GET |
| 302 / 307 | Temporary | A/B tests, maintenance, geo-routing |
| 404 | Not found | Genuinely gone, nothing to offer |
| 410 | Gone permanently | Deliberately removed; crawlers drop it faster |

**Never blanket-redirect a retired site to its homepage.** Map old URLs
to their closest new equivalents; unmapped ones are treated as soft 404s
and the accumulated value evaporates. Chains cost round trips and leak
value at each hop — redirect once, directly to the final URL.

**Keep old domains registered.** An expired domain with inbound links
gets bought, and whatever it points at then carries your former name.

---

## Feeds and syndication — the open web's remaining superpower

RSS and Atom are unglamorous, unmonetized, and still the only
zero-permission distribution channel on the internet. No algorithm, no
account, no rate limit. Podcasts run entirely on RSS. Newsreaders,
aggregators, bots, and automation platforms all consume it.

```html
<link rel="alternate" type="application/rss+xml"
      title="Example — Posts" href="/feed.xml">
```

Full content in the feed, not truncated teasers. Stable `<guid>`s so items
don't reappear as new. Valid `<pubDate>` in RFC-822 format. It costs an
afternoon and a template loop, and it never stops working.

**JSON Feed** is the same idea with less XML pain, and is well supported
by modern readers. **Webmention** and **ActivityPub** extend the same
principle — open protocols, no platform in the middle.

---

## Local and entity presence

For anything geographic, the map result outranks the website result, and
it's a separate system:

- **Claim the business profile** on Google and Apple, and Bing Places.
  Complete every field; category choice matters more than description
  text.
- **NAP consistency** — name, address, phone identical everywhere,
  character for character. Inconsistency splits the entity.
- **Match the structured data on your site** to the profile exactly,
  including the `LocalBusiness` type and hours.
- **Reviews** are ranking input and conversion input at once. Ask
  systematically, respond to all of them, never buy any.
- **Photos with real EXIF and real subjects** outperform stock, measurably.

The general principle beyond local: search engines and language models
both operate on **entities**, not keywords. `sameAs` links from your
`Organization` markup to your profiles elsewhere is you asserting the
identity graph rather than hoping it gets inferred.

---

## Measurement

**Search Console** (and Bing Webmaster Tools) is not analytics — it's the
only view of what the crawler thinks. Non-negotiable, free. Watch:
coverage/indexing status per URL, queries you appear for and your position
in them, Core Web Vitals field data, and manual actions.

**Analytics without surveillance.** Server log analysis (GoAccess),
self-hosted Plausible or Umami, or Cloudflare's aggregate stats give you
the numbers that matter without a consent banner or 40KB of tracker. Page
views, referrers, entry pages, and the queries from Search Console cover
almost every real decision.

**RUM for performance.** The `web-vitals` npm package, or ~20 lines of
`PerformanceObserver`, posting to any endpoint you control:

```js
new PerformanceObserver(list => {
  for (const e of list.getEntries()) navigator.sendBeacon('/rum',
    JSON.stringify({ name: e.name, value: e.startTime, url: location.pathname }));
}).observe({ type: 'largest-contentful-paint', buffered: true });
```

**Look at p75, not the mean.** One 12-second load among ninety fast ones
disappears into an average and is exactly the visit you lost.

---

## What doesn't work, and hasn't for years

Keyword density and stuffing. Exact-match doorway pages. Bought links,
link exchanges, private blog networks. Hidden text and invisible
structured data. Spun or bulk-generated content with no verification.
Cloaking — showing crawlers something different from users. Meta
`keywords`, ignored since roughly 2009.

All of these are detectable at scale, and all of them are more work than
the thing that does work: **a page that is genuinely the best answer to a
real question, marked up so machines can read it, fast enough that people
stay, and linked to from somewhere that already has an audience.**

The unglamorous compounding version: publish something specific and
useful, make it technically legible (fast, semantic, structured), and give
it a permanent URL. Then do it again. The link graph and the index both
reward duration, and almost nobody has the patience — which is precisely
why it still works.

---

## Sources

- **Google Search Central** (`developers.google.com/search`) — the
  documentation. Includes what is and isn't a ranking factor, stated.
- **schema.org** — the vocabulary itself.
- **Open Graph protocol** (`ogp.me`) — the original spec, still accurate.
- **Bing Webmaster Guidelines** — a genuinely different second opinion.
- **web.dev** — Vitals definitions and diagnostics.
- **`robots.txt` is now RFC 9309** — after 25 years as a de facto
  standard.

*Current as of 2026-07. Search behavior, AI-crawler tokens, and rich
result eligibility all change on no schedule — verify against the primary
docs before acting on anything here that carries a number.*
