# Scroll Scene — a full-page WebGL background in ~90 lines of shader

> **Owns:** one technique, all the way down. A single fragment shader that
> paints an entire animated page background and takes **scroll position as
> an input**, plus the plumbing that makes it safe to ship.
> **Not here:** why you'd choose this over a video
> (`DESIGN-LOOPHOLES.md`, §3). Frame-budget theory
> (`INTERNET-SCIENCE.md`).

The runnable version is `template/page-template.html` in this repo — the
shader, the fallbacks, and the reduced-motion branch are all in that one
file, inline.

---

## The mechanic

One canvas, fixed to the viewport at `z-index: 0`, with the page content
above it. One fullscreen triangle. One fragment shader that runs per pixel
per frame and takes exactly three uniforms:

| Uniform | Is | Drives |
|---|---|---|
| `uR` | resolution in pixels | aspect correction |
| `uT` | time in seconds | drift, twinkle, noise |
| `uS` | **scroll progress, 0 → 1** | the entire narrative arc |

`uS` is the interesting one, and it's what no background video can do. The
JS maps `scrollY` across the first few viewport-heights to `0..1`, smooths
it, and feeds it in:

```js
function target() {
  const vh = window.innerHeight;
  return Math.min(1, (window.scrollY || document.documentElement.scrollTop) / (vh * 3.1));
}
// then, per frame: S += (target() - S) * 0.07;   // exponential smoothing
```

**The story is on the scroll axis, not on a timeline.** The reader controls
the playhead. Scroll up and it plays backwards. Stop and it stops. That
coupling is the entire effect: the background is responding to *them*, not
performing at them.

The `* 0.07` smoothing matters more than it looks. Raw scroll position is
jittery (trackpad momentum, scroll snapping, sub-pixel jumps) and coupling
a visual directly to it looks nervous. Exponential smoothing toward a
target gives you weight — the scene feels like it has mass.

---

## Phase gating with `smoothstep`

The whole compositional trick is a handful of overlapping `smoothstep`
ramps off `uS`. Each names a phase and returns 0→1 across a scroll range:

```glsl
float night = smoothstep(.12, .72, s);   // the sky darkens
float glow  = smoothstep(.30, .55, s);   // the small lights appear
float sync  = smoothstep(.55, .96, s);   // ...and fall into one rhythm
```

**Overlap them on purpose.** Non-overlapping phases read as slides
advancing; overlapping ones read as a continuous transformation. `night`
is still finishing when `glow` starts and `sync` is already underway —
that's what makes it feel like weather rather than a state machine.

Then every color and every layer is a `mix()` weighted by one of those
scalars. Nothing in the shader knows about scroll; it only knows about
three numbers between 0 and 1.

---

## The reference scene, layer by layer

Painted back to front, which is also the order to build one in. The
shipped scene is dusk falling over a ridge line, small lights waking in
the valley, and those lights converging from scattered blinking into a
single collective pulse.

1. **Sky gradient** — a warm low, a cool high, `mix`ed by vertical
   position, and the whole palette `mix`ed again by `night`. Two colors,
   two mixes, and this alone would be a respectable background.
2. **Afterglow** — two `exp(-k * length(uv - sun))` falloffs at a point
   low on the horizon, one tight and one wide, faded out by `night`. Two
   exponentials at different rates is how you get a light source that
   looks atmospheric rather than like a radial gradient.
3. **Stars** — a hashed 2px grid, thresholded near 1.0 so only a few
   cells light, multiplied by `night` so they arrive *with* the dark and
   masked to the upper sky.
4. **Ridge stack** — six `fbm` silhouettes in a loop. Near ridges warmer
   and lighter, far ones bluer and darker (aerial perspective, which is
   the one atmospheric cue that reads instantly as depth). A thin mist
   band along each ridge top.
5. **Steady lamps** — two fixed warm points, gated to switch on at dusk.
   **These are load-bearing.** Motion only reads as meaningful against a
   constant; without a steady element the animated layer is just noise.
6. **The small lights** — the payload. A 13× grid, a hash per cell, ~20%
   of cells holding a light at a jittered position with slow wander. Each
   blinks on a sawtooth, `fract(uT * rate + phase)`. As `sync` rises,
   **`rate` converges** toward a common value and **`phase` converges**
   toward zero, so scattered twinkling becomes one pulse. Confined to a
   horizontal band so they sit in the valley.
7. **Grain and vignette** — a little hash noise (`±.025`) and a radial
   darken. Both are cheap, and both are what stop the whole thing from
   looking like clean vector art. Never skip the grain: it hides gradient
   banding for free.

The building blocks under all of it are three small functions — a 2D hash,
value noise built from it, and `fbm` (five octaves of that noise). Roughly
eight lines total, and they're the standard vocabulary; every procedural
scene you'll write uses the same three.

---

## The knobs you'll actually reach for

| Want | Change |
|---|---|
| Slower / faster arc as you scroll | the `vh * 3.1` divisor in `target()`. Bigger = slower |
| Dark arrives sooner / later | the `.12, .72` in `night` |
| More / fewer lights | the `r > .80` threshold (lower = more) |
| Tighter / looser final sync | the `sync` endpoints, and the rate target in `mix(…, .30, sync)` |
| Light color | the `vec3(.80,.94,.38)` on the accumulation line |
| Blink speed | the base rate `.20 + .14 * h21(…)` |
| Ridge count / height | the loop bound `i < 6` and the `base` / `rh` terms |
| Warmth of dusk | the `low` sky color and the afterglow `vec3`s |
| Heavier / lighter grain | the `* .05` on the hash noise line |

---

## Reskinning it to a different subject

The skeleton is a template for *any* "scroll tells a story" background.

1. **Decide the story the scroll tells**, in one sentence, before writing
   any GLSL. "Dusk falls and scattered lights find one rhythm" is a
   sentence. "A cool animated background" is not, and produces mush.
2. **Keep the plumbing** — uniforms, resize handling, the `uS` smoothing,
   the reduced-motion branch, the compile-failure guard. Replace only the
   layer math inside `main()`.
3. **Anchor phases to `smoothstep` ranges of `s`** so the visual beats
   land where the reader physically is on the page. If the page has a
   turning point at 60% scroll, put a phase boundary there.
4. **Keep one steady element** among the animated ones.
5. **Build it back to front, testing after each layer.** A shader is one
   function with no intermediate output; adding six layers before looking
   at it means debugging six things at once.

Other scenes that fit the same skeleton with only `main()` replaced: a
stratosphere-to-ground descent (cloud decks resolving into terrain as `uS`
climbs); a tide going out; a city grid lighting window by window; ink
diffusing through water; a wireframe assembling into a solid. In each case
the phases are `smoothstep`s and the payload is one grid of hashed cells
doing something in gradually less random unison.

---

## The non-negotiables — why the JS is shaped the way it is

These are the difference between a nice effect and something you can put
in front of strangers.

- **Compile failure hides the canvas.** `catch → canvas.style.display =
  'none'`, so a shader typo degrades to the CSS gradient underneath
  instead of a black rectangle over your content. A shader error is
  invisible to the user and silent in production — this guard is the whole
  safety net.
- **`getContext('webgl')` returning null does the same thing.** Old
  hardware, disabled WebGL, some remote desktops.
- **A CSS gradient sits under the canvas, always.** It's the no-JS,
  no-WebGL, and shader-failed fallback simultaneously, and it costs 200
  bytes.
- **`prefers-reduced-motion` renders one static frame** on scroll and
  resize instead of running a `requestAnimationFrame` loop. Not a blank
  space, not a still of frame zero — the correct frame for the current
  scroll position. Motion off, information intact.
- **DPR is capped** (1.25 mobile / 1.6 desktop). A full-screen fragment
  shader at raw retina DPR is 4× the fragments for no visible gain, and it
  cooks phone batteries.
- **One fullscreen triangle, not a quad.** Fewer fragments, no diagonal
  seam, one less vertex.
- **`alpha: false, antialias: false`** on context creation. Neither does
  anything for a fullscreen fragment shader; both cost.
- **The canvas is `aria-hidden="true"`.** It is decoration and must not be
  announced.
- **QA it headlessly, every time.** A dead sky throws no user-visible
  error, so only the console plus a screenshot will tell you it broke:

```
node tools/check.js dist/page.html
```

That checks for console errors, asserts the canvas is still displayed
(i.e. the shader compiled), and drops screenshots at three scroll depths
so you can see the arc. It has caught more than one silent shader typo.

---

## Cost, honestly

~3KB of shader source, uncompressed, inline. No requests, no library, no
build step. Draws in under a millisecond per frame on modest hardware at
capped DPR. Compare: a background video at the same visual weight is
2–20MB, won't reliably autoplay, and can't respond to scroll at all.

Where it's the wrong choice: content-heavy pages where the background
competes for attention, anything that must work in a locked-down
enterprise browser with WebGL disabled (though the fallback covers you),
and any page where the effect isn't saying something. A shader that
doesn't carry an idea is a 3KB way to look busy.

---

## Learning the vocabulary

- **The Book of Shaders**, Patricio Gonzalez Vivo — the canonical
  introduction, free, interactive. Chapters on noise and shaping functions
  are exactly what's used above.
- **Inigo Quilez's articles** (`iquilezles.org`) — distance functions,
  `smoothstep` tricks, palette generation. The primary source for most of
  the idioms in this file.
- **Shadertoy** — read other people's `main()`. The convention there is a
  `iTime`/`iResolution` pair; swapping in a scroll uniform is the only
  adaptation needed.
- **thebookofshaders.com/appendix** and **WebGL Fundamentals** — for the
  plumbing side (buffers, programs, uniforms) if the JS above looks
  arbitrary.
