# Cinematic scroll — tours, flyovers and walkthroughs

> **Owns:** techniques that map scroll position to a camera — video scrub,
> image sequences, scroll-driven 3D, photogrammetry and Gaussian splats.
> Which to reach for, what each costs to produce and to serve, and what
> each does when it fails.
> **Not here:** the WebGL background that reacts to scroll without being a
> camera (`SCROLL-SCENE.md`). General motion and reduced-motion policy
> (`DESIGN.md`). Getting the page found (`MASTERING-THE-INTERNET.md`).

The effect is always the same promise: **the visitor's scroll becomes the
camera.** They scroll, and they move through a room, along a ridge, around
a product. Nothing else on the open web buys as much perceived production
value per unit of engineering — and nothing else fails as expensively when
it's built on the wrong substrate.

There are four substrates. Picking the wrong one is the mistake, not the
implementation.

---

## The four methods, honestly

### 1 · Video scrub

A stabilized camera walks a path; JavaScript maps scroll position to the
video's `currentTime`.

**The appeal is real:** one file, compresses beautifully (inter-frame
compression is exactly what video codecs are for), and the source is a
normal shoot.

**The problem is seeking.** Video is compressed as occasional keyframes
plus differences. Asking for an arbitrary timestamp means decoding forward
from the previous keyframe, so scrubbing — especially *backward* — is
either coarse or expensive. The documented workaround is encoding at or
near all-keyframe, which throws away most of the compression that made
video attractive. Backward scrubbing and frame-accurate control remain the
known weak points of the video approach, and iOS has historically added
its own constraints around inline playback and programmatic seeking.

**Reach for it when:** the motion is long, mostly forward, and precision
doesn't matter — an ambient background that drifts as you scroll.

**Don't when:** the visitor is meant to stop, reverse, and study a frame.
That is the whole point of a property walkthrough, and it's the thing
video scrub is worst at.

### 2 · Image sequence on canvas — *the workhorse*

The same shoot, exported as numbered stills, drawn to a `<canvas>` at the
frame the scroll position selects.

This is what the famous product pages actually do. Apple's AirPods Pro
sequence is a brute-force preload of individual frames — **65 PNGs
totalling 15.2 MB** in the version CSS-Tricks dissected. Canvas remains
the most performance-oriented option for this effect.

Every frame is independent, so seeking is free and identical in both
directions. There is no codec, no keyframe spacing, no `currentTime`
rounding. The cost is bytes and requests, and both are tunable in a way
video's seek behavior is not.

**A measured example.** The reference implementation in
`library/snippets/scroll-scrub.html`, against a 60-frame 1600×900
sequence at JPEG q72:

| | |
|---|---|
| Sequence weight | **1.32 MB total, ~21 KB/frame** |
| First frame painted | **132 ms** (localhost, so decode-bound not network-bound) |
| Scrub behavior | forward and backward both exact; frame restored on return |
| Degradation | 11/11 checks pass — no-JS, reduced-motion, save-data, no-frames |

Note what the numbers do *not* say: 132 ms is a local-disk figure. On a
real connection the first frame is a network round trip, and the full
sequence is 1.32 MB that a phone on a rural LTE tail will feel.

**Budget honestly.** Frame count × frame weight is the whole cost, and it
is linear. 60 frames at 20 KB is a MB. 300 frames at 60 KB is 18 MB, which
is not a web page. Get there by cutting **frame count first** (a 24-frame
sequence eased well reads as smooth), then dimensions, then quality —
in that order, because frame count is the only one that also cuts requests
and decode work.

### 3 · Scroll-driven 3D — mesh photogrammetry

Overlapping captures are solved into a textured triangle mesh; the mesh
loads in a 3D engine and scroll drives a camera along a fixed path.

Photogrammetry produces the same kind of geometry games and CAD use, which
is its advantage: it is a *real* asset. It can be relit, measured,
collided against, and edited. Compress it with Draco or meshopt geometry
compression and KTX2/Basis textures, or it will not ship.

Where it struggles is exactly where interiors live: glass, gloss,
vegetation, fabric, and anything reflective. Those become melted geometry
and smeared texture, because a single mesh cannot represent a surface
whose appearance depends on where you're standing.

### 4 · Scroll-driven 3D — Gaussian splats

The current alternative to a mesh. The scene is stored as millions of
colored, semi-transparent ellipsoids rather than a surface, and it renders
in real time in a browser. It looks dramatically more photorealistic than
mesh photogrammetry on precisely the materials meshes ruin — vegetation,
hair, fabric, glass.

**Status, as of mid-2026.** Moving fast, and worth re-checking before
committing:

- **PLY is still the most widely supported delivery format**; SPZ is the
  compact format aimed at progressive web delivery.
- **Khronos `KHR_gaussian_splatting`** — a glTF extension — was tracking
  ratification around Q2 2026, with SPZ streaming as a follow-on. OGC 3D
  Tiles 2.0 treats splats as a first-class tile type; MPEG has splat
  coding work underway.
- **Renderers are WebGL today, WebGPU next.** Native compute-shader
  rendering is the expected near-term step.

**The catch is weight and it is not small.** Delivery sizes in the tens of
megabytes are normal for a good capture, and getting one to load fast on a
phone over mobile data takes real optimization work. A splat is not a
drop-in for a hero image; it is a feature with a loading strategy.

**And the capture is the product.** Bad input gives floaters and artifacts
that are hard to fix afterward. The photographer matters more than the
developer here — even, overlapping coverage, controlled exposure, no
moving subjects.

---

## Choosing: match the substrate to the job

| The visitor needs to… | Use | Why |
|---|---|---|
| feel the place, once, on the way past | image sequence | cheapest, degrades to a still, works everywhere |
| move through a specific route | image sequence | exact in both directions |
| linger on an ambient background | video scrub *or* shader | precision doesn't matter |
| judge a space they might rent | splat or mesh | free look beats a fixed path |
| verify dimensions, layout, fit | mesh | it's real geometry; splats aren't surfaces |
| see one object from all sides | image sequence (turntable) | a 36-frame orbit beats a 30 MB model |

The honest default for a small business site is **the image sequence**,
and the honest default for most pages is **none of these** — a good
photograph loads in 40 KB and never fails.

---

## It has to fit the trade

A cinematic tour is not one feature applied to every site. Each trade
asks a different question at the moment the visitor is most engaged, and
the technique should answer *that* question:

- **Lodging.** The question is *what is it actually like there.* A route
  matters — arrive, enter, move through, step onto the deck. Image
  sequence along the walk, or a splat if the visitor should be free to
  look around. The tour ends at a date picker, not at a phone number.
- **Trades and service work.** The question is *can you fix this, now.*
  A cinematic tour of a plumbing van is a distraction with a loading
  cost. The motion budget belongs on a before/after wipe or a
  cutaway of the actual repair — short, specific, close to the call
  button. Emergency work rewards a fast page far more than a beautiful one.
- **Venues and gatherings.** The question is *what is it like in the
  room, full.* Sightline from a seat, room at capacity — a short sequence
  from two or three vantage points, next to the dates.
- **Land and property.** The question is *what surrounds it.* This is the
  one case where a flyover genuinely earns its weight: approach, parcel,
  and what's around it.

Same family look, different job. The invariant is the palette, the type
system, the scroll grammar and the failure behavior; the **dialect** is
which question the motion answers and where it deposits the visitor. One
core, per-trade dialect — the same rule this repo applies to documents.

---

## Driving it: platform or library

**CSS scroll-driven animations** (`animation-timeline: scroll()` and
`view()`) move this off the main thread with no JavaScript at all. Support
as of mid-2026:

- Chrome/Edge since **115** (July 2023)
- Safari since **26** (September 2025), with threaded scroll-driven
  animations in 26.4
- **Firefox stable still has it behind a flag** as of 152 (June 2026) —
  on by default in Nightly, and a named Interop 2026 priority

That leaves it around **82–84% globally and explicitly not Baseline**,
blocked by Firefox. Which is fine — this is the ideal progressive
enhancement. Use it for reveals, parallax and progress indicators inside
`@supports (animation-timeline: view())`, and let everything else get the
static layout. Do not use it for anything load-bearing.

**GSAP's ScrollTrigger** is the standard answer for the complex cases, and
the licensing changed: Webflow acquired GreenSock in **October 2024** and
in **April 2025** made the entire library — including every formerly paid
Club plugin, ScrollTrigger among them — **free, including for commercial
use**.

That removes the cost objection but not the dependency objection. The rule
that still holds: a frame scrubber is ~150 lines of plain JavaScript
(`library/snippets/scroll-scrub.html` is a working one with no
dependencies). Reach for ScrollTrigger when you need *orchestration* —
many pinned, overlapping, interdependent timelines — not to map one number
to one frame index.

---

## The rules that keep it from becoming a liability

**Never hijack the scroll.** Do not intercept wheel events to "advance"
the scene. It breaks keyboard scrolling, trackpad momentum, screen
readers, find-in-page, and the browser's own scroll restoration. Map
position to state and let the scrollbar be the scrollbar.

**Content lives in the HTML.** Every caption, price, dimension and claim
belongs in the document as text. The sequence carries *no information* the
document doesn't. Then a crawler, a reader with scripting off, and a
screen reader all get the whole page.

**Honor `prefers-reduced-motion`.** A scroll-locked camera move is exactly
the kind of vestibular trigger the query exists for. Show one
representative frame and stop. This isn't a lesser experience; for that
visitor it's the correct one.

**Honor `Save-Data`, and gate on visibility.** Don't fetch megabytes for a
scene the visitor may never reach. Load when it's plausibly on the way in,
and not before.

**The poster is the real deliverable.** One well-chosen still, with real
`alt` text, is what a link preview shows, what a crawler indexes, what a
reduced-motion visitor sees, and what remains when anything at all goes
wrong. Choose it as carefully as the sequence.

**Reveal only after the first paint.** A canvas that hasn't drawn yet must
never replace a good poster — hold the poster until a frame is actually on
screen. Getting this backwards turns a slow connection into a blank
rectangle.

---

## Production reality

The web work is the cheap half. What the technique actually costs:

- **A stabilized rig and someone who can walk a repeatable path.** The
  path has to be smooth, level, and the same every take.
- **Controlled, even light.** Auto-exposure drift between frames reads as
  flicker the moment the sequence scrubs.
- **Empty rooms and no moving subjects**, for splats and photogrammetry
  especially — anything that moves becomes an artifact.
- **A re-shoot budget.** Furniture moves; seasons change; the deck gets
  restained.

Before commissioning any of it, price the alternative honestly: six
excellent photographs, correctly sized and lazy-loaded, cost a fraction
and never fail. The tour has to beat *that*, not beat nothing.

---

## Reference implementation

`library/snippets/scroll-scrub.html` — a dependency-free scroll-scrub
sequence that generates its own frames so it runs from disk. Point `SEQ.src`
at a real sequence to use it. Verified: forward and backward scrub exact,
canvas revealed only after first paint, and correct behavior with
scripting disabled, reduced motion requested, and Save-Data on.

---

## Sources and date

Checked **2026-07-30**. Browser support, format standards and licensing
in this area all move — re-check before committing to any of it.

- Scroll-driven animation support: [web-features explorer](https://web-platform-dx.github.io/web-features-explorer/features/scroll-driven-animations/),
  [caniuse](https://caniuse.com/mdn-css_properties_animation-timeline_scroll),
  [MDN `animation-timeline`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/animation-timeline),
  [MDN scroll-driven animations guide](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations)
- GSAP licensing: [Webflow announcement](https://webflow.com/updates/gsap-becomes-free),
  [CSS-Tricks](https://css-tricks.com/gsap-is-now-completely-free-even-for-commercial-use/)
- Image sequences and the Apple pattern: [CSS-Tricks](https://css-tricks.com/lets-make-one-of-those-fancy-scrolling-animations-used-on-apple-product-pages/),
  [video scrubbing notes](https://www.ghosh.dev/posts/playing-with-video-scrubbing-animations-on-the-web/)
- Gaussian splatting status and standards: [THE FUTURE 3D](https://www.thefuture3d.com/blog/state-of-gaussian-splatting-2026/),
  [Splatware comparison](https://splatware.com/learn/photogrammetry-vs-gaussian-splatting),
  [field report](https://amplifiedcreations.com/journal/gaussian-splatting-production-ready-2026)
- Weight, timing and degradation figures: measured in this repo against
  `library/snippets/scroll-scrub.html`, 2026-07-30.
