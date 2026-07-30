# Open Source — building a professional web presence for nothing, legally

> **Owns:** the free and open parts. Licenses and what they actually
> require, fonts, icons, images, data, hosting, self-hosting, and the
> toolchain — plus the compliance details that turn "free" into "free and
> defensible."
> **Not here:** how to use them well (`DESIGN.md`,
> `DESIGN-LOOPHOLES.md`). Distribution (`MASTERING-THE-INTERNET.md`).

Nearly the entire stack needed to design, build, host, secure, and measure
a professional website is available at no cost under licenses that permit
commercial use. The constraint is not money; it's knowing what exists and
honoring the terms.

---

## Licenses first, because this is where people get hurt

**"Free to download" is not a license.** Every asset and dependency you
ship carries terms. Read them once per category and you'll never think
about it again.

### Permissive — safe for commercial work, minimal obligation

| License | Obligation | Note |
|---|---|---|
| **MIT** | Keep the copyright + license text | The default for good reason |
| **BSD 2/3-clause** | Same; 3-clause also bars using the author's name to endorse | Equivalent in practice |
| **Apache 2.0** | Keep notices, state changes, `NOTICE` file if present | Includes an explicit patent grant — the reason to prefer it |
| **ISC** | Keep the notice | MIT, shorter |
| **Unlicense / CC0 / 0BSD** | None | Public-domain dedication |
| **SIL OFL 1.1** | Keep the license with the font; **modified versions must be renamed** | Nearly every open font. Web-embedding is explicitly allowed |

### Copyleft — usable, but understand the reach

| License | Trigger | Practical meaning |
|---|---|---|
| **GPL 2/3** | Distributing the binary/work | Derivative works must be GPL too |
| **LGPL** | Modifying the library itself | Linking is fine; keep it replaceable |
| **AGPL 3** | **Network use counts as distribution** | Running a modified version as a web service obliges you to offer source. This is why some companies ban it |
| **MPL 2.0** | Per-file | Modified MPL files stay MPL; the rest of your code doesn't |

### Creative Commons, for content and media

- **CC0** — public domain. No attribution required (giving it anyway is
  good manners).
- **CC BY** — attribution required. Commercial use fine.
- **CC BY-SA** — attribution + derivatives must share alike. Fine for
  content; a real constraint if you remix it into proprietary material.
- **CC BY-NC** — **no commercial use.** A client site is commercial. This
  is the one that catches people.
- **CC BY-ND** — no derivatives. Cropping or recoloring is a derivative.

### The habits that keep this clean

1. **Record the license and source URL for every asset, at the moment you
   take it.** A `CREDITS.md` or a spreadsheet. Reconstructing provenance
   two years later is genuinely impossible.
2. **Screenshot the license page.** Terms change; your grant was under the
   old ones, and you'll want the evidence.
3. **"NC" and "ND" mean no.** Don't argue with them.
4. **Run a license scan** on dependencies: `npx license-checker
   --summary`, or `pip-licenses`. Look for AGPL and GPL first.
5. **Attribution goes somewhere real** — a credits page, a footer link, a
   comment in the source. Buried in a build artifact isn't attribution.
6. **Trademark ≠ license.** An open-source *license* on a logo does not
   grant you use of the *mark*. Company logos are almost always
   trademarked regardless of file license.
7. **Web-font licensing is its own category.** Commercial fonts often
   license desktop and web separately, and price web by pageview. OFL
   fonts have no such limit — which is a large part of their value.

---

## Type

**Where to look:**
- **Google Fonts** (`fonts.google.com`) — ~1,600 families, nearly all OFL.
  **Download and self-host.** Hotlinking the CDN adds a third-party
  origin, an extra connection, a privacy exposure, and (in Germany, per a
  2022 ruling) a GDPR problem. Self-hosting is faster anyway.
- **Fontsource** (`fontsource.org`) — the same fonts packaged for
  self-hosting, per-weight, per-subset, as npm packages or plain files.
- **Google Fonts Knowledge / Fontshare / Font Squirrel** — curated, mixed
  licenses. Check each.
- **The League of Moveable Type**, **Velvetyne**, **Collletttivo** —
  independent open foundries with much more character than the popular
  Google set.
- **Open Foundry**, **Use & Modify** — good browsing for OFL faces with
  personality.

**Pairings that hold up, all open:**

| Use | Display | Body | Mono |
|---|---|---|---|
| Editorial / warm | Playfair Display | Newsreader | IBM Plex Mono |
| Modern / neutral | Inter (tight) | Inter | JetBrains Mono |
| Literary | Fraunces | Source Serif 4 | Space Mono |
| Technical | Space Grotesk | Public Sans | IBM Plex Mono |
| Geometric | Outfit | Work Sans | DM Mono |

**Preparation, always:**
1. Get woff2. It's ~30% smaller than woff and universally supported;
   nothing else is needed in 2026.
2. **Subset.** `fonttools`' `pyftsubset` cuts a 300KB face to 30KB by
   dropping the glyphs you don't use:
   ```
   pyftsubset Face.ttf --flavor=woff2 --layout-features='*' \
     --unicodes=U+0000-00FF,U+2018-201D,U+2013-2014,U+2026 \
     --output-file=face-latin.woff2
   ```
3. **Prefer one variable font** over four static weights.
4. `font-display: swap`, and matched fallback metrics (`size-adjust`,
   `ascent-override`) so the swap doesn't shift layout.
5. To embed as base64 (the one-file approach):
   `base64 -w0 face.woff2` on Linux, `base64 -i face.woff2` on macOS.
   `tools/extract_fonts.py` in this repo pulls embedded faces back out of
   any page that already has them.

---

## Icons and illustration

- **Lucide** (ISC) — the actively maintained Feather successor. Clean,
  consistent, ~1,500 icons, tree-shakeable or copy-paste SVG.
- **Heroicons** (MIT) — two weights, pairs naturally with utility CSS.
- **Phosphor** (MIT) — six weights, ~9,000 icons. Best range.
- **Tabler Icons** (MIT) — ~5,700, very consistent stroke.
- **Bootstrap Icons** (MIT), **Remix Icon** (Apache 2.0), **Material
  Symbols** (Apache 2.0) — large, dependable.
- **Simple Icons** (CC0) — brand logos. **The files are CC0; the
  trademarks are not.** Fine for "log in with X," not for implying
  endorsement.
- **undraw** (open, no attribution) and **Humaaans** (CC BY) — vector
  illustration you can recolor to your palette.

**Copy the SVG in; don't install an icon library** for six icons. Inline
SVG with `stroke="currentColor"` inherits color for free and costs no
request.

---

## Images

**Free, commercial-use, no attribution required:** Unsplash, Pexels,
Pixabay (each has its own license — Unsplash's permits commercial use but
forbids compiling a competing stock service).

**Public domain, properly:**
- **Wikimedia Commons** — vast; check each file's individual license.
- **Openverse** (`openverse.org`) — searches ~700M CC-licensed works with
  license filters that work.
- **The Met**, **Rijksmuseum**, **Smithsonian Open Access**, **NYPL
  Digital Collections**, **Library of Congress** — museum-grade CC0
  imagery, high resolution, and far more distinctive than stock.
- **NASA Image Library**, **USGS**, **NOAA** — US federal works are
  generally public domain. Excellent for texture, terrain, and sky.

**The honest caveat:** free stock is recognizable as free stock. A
gradient, a shader, a duotone-treated public-domain archive image, or a
photo you took yourself all read as more considered
(`DESIGN-LOOPHOLES.md`).

**Processing, all free and local:**
- **Sharp** (Node) or **Pillow** (Python) — resize and convert in a
  script.
- **Squoosh** (`squoosh.app`) — browser-based, nothing uploaded, excellent
  AVIF/WebP encoders with a visual quality slider.
- **ImageMagick** / **libvips** — batch work; libvips is dramatically
  faster on large files.
- **oxipng**, **jpegoptim**, **svgo** — lossless final squeeze.
- **GIMP**, **Krita**, **Inkscape** (vector), **darktable** (raw), **Penpot**
  (Figma-alternative UI design, self-hostable).

**The delivery pattern worth memorizing:**

```html
<picture>
  <source type="image/avif" srcset="hero-800.avif 800w, hero-1600.avif 1600w"
          sizes="(max-width: 800px) 100vw, 800px">
  <source type="image/webp" srcset="hero-800.webp 800w, hero-1600.webp 1600w"
          sizes="(max-width: 800px) 100vw, 800px">
  <img src="hero-800.jpg" width="1600" height="900" alt="Describe the function"
       fetchpriority="high" decoding="async">
</picture>
```

AVIF is ~50% smaller than JPEG at equal perceived quality; WebP ~30%.
`width`/`height` prevent layout shift. Never `loading="lazy"` on the LCP
image.

---

## Hosting, TLS, and infrastructure

**Static hosting, free tier, HTTPS and CDN included:** Cloudflare Pages
(no bandwidth cap), Netlify, Vercel, GitHub Pages, GitLab Pages,
Codeberg Pages, Deno Deploy, Surge.

**Certificates:** Let's Encrypt via `certbot` or `acme.sh`, or ZeroSSL.
Free, automated, 90-day renewal. There is no remaining reason to pay for a
DV certificate. (Pointing the domain: `DNS-RUNBOOK.md`.)

**DNS:** Cloudflare (free, fast, anycast), deSEC (non-profit, free, DNSSEC
by default), Bunny, or your registrar's.

**Edge compute, free tiers:** Cloudflare Workers, Deno Deploy, Netlify and
Vercel functions. Enough for form handling, redirects, OG image
generation, and API proxying without a server.

**Databases and backends with real free tiers:** Supabase and Neon
(Postgres), Turso and Cloudflare D1 (SQLite at the edge), PocketBase (one
Go binary — SQLite, auth, file storage, admin UI), Appwrite, Directus.

**Self-hosting, when you'd rather own it:** Caddy (automatic HTTPS with
zero configuration — the single easiest web server to run correctly),
Nginx, Docker + Compose, Coolify or Dokku for a Heroku-like deploy flow on
your own box. A $5/month VPS runs a great deal more than people expect.

**Site generators:** Eleventy (the most flexible, least opinionated),
Astro (ships zero JS by default), Hugo (fastest builds by an order of
magnitude), Jekyll, SvelteKit, Nuxt, Zola, Pelican. Or — genuinely — a
Python script and a template string; `tools/build.py` here is 57 lines and
does the job for a single page.

**Analytics without surveillance:** GoAccess (parses server logs),
Plausible or Umami (self-hosted), Matomo, Counter.dev. No consent banner
required when nothing personal is stored.

**Forms without a backend:** a Worker, an edge function, or a
self-hosted Formbricks / Baserow.

**Everything else, briefly:** Playwright (browser automation and
screenshots), Lighthouse CI, axe-core (accessibility), Pa11y, `git`,
`ripgrep`, `jq`, `curl`, `dig`, `ffmpeg`, Pandoc, SQLite. Together,
professional-grade infrastructure at zero licensing cost.

---

## Data

Free, redistributable datasets are the raw material for the kind of page
nobody else has.

- **OpenStreetMap** (ODbL — attribution + share-alike on derived
  databases) with **Overpass API** for querying. **Nominatim** for
  geocoding (respect the usage policy or self-host).
- **US Census / American Community Survey** — public domain, with a real
  API. Demographics down to block group.
- **data.gov**, **data.gov.uk**, **EU Open Data Portal**, and most
  state/county open-data portals — public records, usually CC0 or
  equivalent.
- **Wikidata** (CC0) — a queryable knowledge graph via SPARQL. Structured
  facts about essentially everything.
- **OpenCorporates**, **SEC EDGAR** (public domain), **USPTO** — company
  and filing data.
- **GeoNames** (CC BY), **Natural Earth** (public domain) — place names
  and map geometry.
- **Our World in Data** (CC BY) — cleaned, sourced global datasets.

**The rules that keep this legitimate:** read the terms of service before
scraping — public and permitted are different questions. Honor
`robots.txt`. Rate-limit and identify your agent honestly. Prefer a
documented API or a bulk download to scraping a rendered page. Cache
locally so you fetch once. Attribute as the license requires (ODbL and CC
BY both require it, prominently). Publish your own derived work under
compatible terms, and cite the source with an as-of date so it can be
re-checked.

---

## Contributing back, briefly

Using this much free labor and giving nothing back is a choice worth
noticing. The cheap forms of reciprocity: file precise bug reports with
reproductions, improve documentation (the most-needed and least-done),
publish your own tooling under MIT, sponsor a maintainer whose work you
depend on daily, and answer a question in someone's issue tracker. None of
it requires being a systems programmer.

---

## Sources

- **choosealicense.com** — GitHub's plain-language license comparison.
- **tldrlegal.com** — licenses summarized, with the obligations named.
- **SPDX License List** — the canonical identifiers (`MIT`, `Apache-2.0`)
  used by tooling.
- **Open Source Initiative** (`opensource.org/licenses`) — the approved
  list and full texts.
- **Creative Commons** (`creativecommons.org/licenses`) — the CC terms and
  the license chooser.
- **SIL Open Font License FAQ** — the authority on what you may do with an
  OFL font, including embedding and renaming.

*This is a summary written by a developer, not legal advice. For anything
where the exposure is real — a copyleft dependency in a commercial
product, a trademark question, a redistributed dataset — the terms
themselves and a lawyer are the sources, not this file.*
