# Design Loopholes — small honest inputs, disproportionate outputs

> **Owns:** the leverage points. Places where the web platform hands you a
> large visual or performance effect for a small, honest input — one
> property instead of a library, a gradient instead of a photograph, math
> instead of an asset.
> **Not here:** the fundamentals the tricks sit on (`DESIGN.md`). The
> transport-layer explanations (`INTERNET-SCIENCE.md`). The deep shader
> case study (`SCROLL-SCENE.md`).

A loophole here is not a way to fool a user or a search engine. It's an
**asymmetry**: the platform will do something expensive-looking for almost
nothing, if you know the property exists. The test for every entry below
is *does it hold up when someone reads the source?*

---

## The asymmetries, ranked by payoff per line

### 1 · One file, zero requests

Inline the CSS, inline the JS, base64 the fonts. The entire page is one
HTTP response, arriving in the first flight or two.

**What you get:** no CDN dependency, no waterfall, no FOUT, no build
pipeline, no `node_modules`. It can be emailed as an attachment, opened
from a thumb drive, hosted on anything, and it will still work in a
decade. A dead font CDN cannot break it because there is nothing to fetch.

**What it costs:** ~300KB of base64 for six font faces, and no cross-page
caching of shared assets. Worth it for a landing page, a pitch, a
one-pager, a résumé, a proposal. Not worth it for a 40-page site — there,
fingerprint and cache normally.

Working implementation: `template/page-template.html` plus
`tools/build.py` in this repo.

### 2 · A gradient instead of a photograph

A hero photo is 200–800KB, needs art direction at four sizes, and looks
like everyone else's stock. A multi-stop gradient is ~200 bytes, scales to
any viewport, and can be genuinely beautiful.

```css
background: linear-gradient(#131c2b 0%, #2b3446 40%, #6a5a54 72%,
                            #c98f5a 88%, #1a2420 100%);
```

The trick is **more stops than you think, at uneven positions.** Two-stop
gradients look like a default. Five stops with an asymmetric distribution
reads as a photograph of a sky. Add `radial-gradient` blobs at low opacity
over it for depth, and a fine noise layer to defeat banding:

```css
/* grain, no image file: an inline SVG turbulence as a data URI */
background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence baseFrequency='0.8'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
```

`color-mix()` and OKLCH interpolation give you gradients that don't pass
through muddy grey in the middle — the historical reason gradients looked
cheap.

### 3 · A fragment shader instead of a video

A background video is 2–20MB, won't autoplay reliably, drains battery, and
can't respond to anything. One full-screen fragment shader is ~3KB of
text, draws at 60fps, and can take *scroll position as an input* — which
no video can.

This is the single largest visual-return-per-byte on the web platform. It
needs one canvas, one fullscreen triangle, and three uniforms
(resolution, time, scroll). Full annotated implementation and the reskin
recipe: **`SCROLL-SCENE.md`**.

Non-negotiable safety rail: on shader compile failure, hide the canvas so
the CSS gradient underneath shows. A silent black box is the failure mode
to design against.

### 4 · `backdrop-filter` — glass for one line

```css
.panel { background: rgba(8,15,12,.7); backdrop-filter: blur(12px) saturate(140%); }
```

Content over an image or animation stays legible while the background
stays visible. This effect used to require a screenshot-and-blur pipeline.
Keep a solid `background` underneath as the fallback, and don't animate a
`backdrop-filter` element — it's expensive per frame.

### 5 · `content-visibility: auto`

```css
section { content-visibility: auto; contain-intrinsic-size: auto 800px; }
```

The browser skips layout and paint for off-screen sections entirely. On a
long page this is close to an order-of-magnitude improvement in initial
render for one declaration. `contain-intrinsic-size` is required or the
scrollbar jumps as sections realize their height.

### 6 · CSS scroll-driven animations — no JavaScript at all

```css
@keyframes reveal { from { opacity: 0; transform: translateY(24px); } }
.card {
  animation: reveal linear both;
  animation-timeline: view();
  animation-range: entry 10% cover 35%;
}
```

Scroll-linked reveals and progress bars, running off the main thread, with
no `IntersectionObserver` and no scroll listener. Smoother than the JS
version because it isn't on the main thread at all. Support is good in
Chromium as of 2026 and progressing elsewhere — and it degrades to
"content is simply visible," which is the correct fallback.

The JS fallback worth keeping for now is `IntersectionObserver`, which is
still far cheaper than a scroll handler:

```js
const io = new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add('on'); io.unobserve(e.target); }
}), { threshold: 0.18 });
document.querySelectorAll('.rv').forEach(el => io.observe(el));
```

### 7 · Variable fonts

One file, every weight, plus every weight *between*. Two static faces
(400 + 700) cost roughly what one variable font costs, and the variable
font gives you 100–900 continuously, optical sizing, and animatable
weight.

```css
@font-face { font-family: 'X'; src: url(x.woff2) format('woff2-variations');
             font-weight: 100 900; font-display: swap; }
h1 { font-variation-settings: 'wght' 620, 'opsz' 48; }
```

`font-display: swap` renders in a fallback immediately rather than showing
nothing. Pair with `size-adjust` and matched fallback metrics so the swap
doesn't shift layout.

### 8 · `clamp()` deletes your breakpoints

```css
h1      { font-size: clamp(2rem, 6vw, 4.5rem); }
.wrap   { width: min(100% - 3rem, 70ch); margin-inline: auto; }
.grid   { grid-template-columns: repeat(auto-fit, minmax(min(280px,100%), 1fr)); }
```

Three lines replacing a stack of media queries, and they're correct at
*every* width, including the ones you didn't test. Keep a `rem` term in
the middle argument so browser zoom still works.

### 9 · `:has()` — the parent selector, finally

```css
.card:has(img)            { grid-template-columns: 160px 1fr; }
form:has(:invalid) button { opacity: .5; pointer-events: none; }
body:has(dialog[open])    { overflow: hidden; }
```

Each of these previously required JavaScript to toggle a class. Now it's
one selector, and it can't get out of sync with the DOM.

### 10 · `<dialog>`, `popover`, `details` — free components

`<dialog>` gives you a real modal: focus trapping, `Escape` to close,
inert background, `::backdrop` styling. The `popover` attribute gives you
tooltips and menus with light-dismiss behavior. `<details>`/`<summary>` is
an accordion with keyboard support and no script.

Each replaces a dependency that historically shipped 10–40KB and got the
accessibility subtly wrong.

### 11 · Perceived performance beats real performance

Users don't experience milliseconds; they experience uncertainty.
- **Optimistic UI** — show the result immediately, reconcile after.
- **Skeletons matching the final layout** — not a spinner. A spinner says
  "wait"; a skeleton says "here's what's coming" and produces no CLS.
- **`<link rel="preconnect">`** on a third-party origin you *will* use —
  DNS, TCP and TLS happen during idle time before the request exists.
- **Speculation Rules** — prerender the page the user is most likely to
  click next; it arrives instantly.
- **`fetchpriority="high"`** on the hero image, and never
  `loading="lazy"` on it.

### 12 · Generate images from HTML

Need 200 Open Graph cards, or a diagram, or a certificate? Render an HTML
page headlessly to PNG. Same fonts, same palette, same CSS you already
wrote, one template, zero design tools.

```js
await page.setViewportSize({ width: 1200, height: 630 });
await page.screenshot({ path: 'og.png' });
```

`tools/check.js` in this repo shows the mechanics.

### 13 · SVG is code, so it's cheap

Inline SVG is styleable with CSS, animatable, scales infinitely,
compresses like text, and needs no request. Icons, logos, diagrams,
dividers, and background textures all belong here. `currentColor` makes an
icon inherit its context automatically:

```html
<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5">…</svg>
```

`stroke-dasharray` + `stroke-dashoffset` gives you a line that draws
itself in two properties.

### 14 · `system-ui` costs nothing and looks native

```css
font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
```

Zero bytes, zero requests, no FOUT, and it looks correct on every OS
because it *is* the OS font. For interface-heavy work this is often the
right answer, not a compromise.

---

## Loopholes that are actually traps

Worth naming, because they get recommended.

| Tempting | Why it backfires |
|---|---|
| Hero image with `loading="lazy"` | Delays your own LCP element. Use `fetchpriority="high"` |
| `will-change` on many elements | Forces layers, eats GPU memory, makes things slower. Use sparingly and remove after |
| Custom scrollbars / scroll-jacking | Breaks the user's expectations, muscle memory, and often keyboard scrolling |
| Infinite scroll on content pages | No footer access, no deep links, no bookmarks, worse indexing |
| `!important` to win a fight | The fight comes back bigger. Fix the specificity |
| Autoplaying video with sound | Blocked by every browser, and rightly |
| Fixed `100vh` on mobile | Ignores collapsing browser chrome. Use `dvh` |
| Disabling zoom for a "cleaner" look | Straightforward accessibility harm |
| Ultra-thin light-grey body text | Looks refined in Figma, unreadable in sunlight, fails contrast |
| Text baked into images | Not selectable, searchable, translatable, or zoomable |
| 12 web font files "for flexibility" | One variable font does more for less |
| Framework for a static page | 90KB of runtime so a heading can animate |

---

## The five questions that generate new loopholes

The list above will date. The method won't:

1. **Can the platform already do this?** Check MDN before installing
   anything. The last few years moved `:has()`, container queries,
   `dialog`, view transitions, scroll-driven animations, and OKLCH from
   "library" to "built in."
2. **Can this asset be math instead of a file?** Gradients, shaders, SVG,
   CSS shapes, procedural noise. A file needs a request and a cache
   entry; math needs neither.
3. **What's the cheapest thing that produces this feeling?** Users
   respond to contrast, motion timing, space, and typography — not to
   asset budgets. A 3KB shader can out-impress a 4MB video.
4. **What does the browser do for free that I'm re-implementing?** Focus
   management, form validation, lazy loading, date parsing, scroll
   anchoring, back/forward cache. Every one has a native version that's
   more correct than the hand-rolled one.
5. **What happens when this fails?** The best techniques degrade to
   something acceptable — a gradient under the shader, a fallback font, a
   visible section that didn't animate. The worst ones degrade to a blank
   page. That single question separates a technique from a liability.
