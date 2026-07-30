# Design — the fundamentals, stated as decisions

> **Owns:** the craft. Type, scale, color, space, hierarchy, motion, and
> accessibility — the small set of choices that separate a page that looks
> considered from one that looks assembled.
> **Not here:** the high-leverage tricks (`DESIGN-LOOPHOLES.md`). Where
> to get the fonts and images (`OPEN-SOURCE.md`). Performance
> (`INTERNET-SCIENCE.md`).

Design on the web is not decoration applied at the end. It's a series of
constraints chosen early enough that everything after them is easy. The
list below is the whole set that matters for most pages, in the order
you'd decide them.

---

## The one idea underneath all of it

**Nothing is neutral; everything is either deliberate or default.** A page
looks amateur not because its choices are wrong but because it has no
choices — 16px Arial, `#0000EE` links, whatever margin the browser
shipped, three fonts that arrived with three components. The fastest way
to make something look designed is to *decide* every value in a small
system and then never deviate.

Amateur work has infinite variety in the wrong places: nine font sizes,
eleven greys, spacing that's 13px here and 17px there. Professional work
is repetitive up close and rich at a distance.

---

## 1 · Type

Type is 90% of most web pages. Get it right and you can ship almost
nothing else.

**Measure (line length).** 45–75 characters per line, 66 as the classic
target. Too long and the eye loses the return; too short and rhythm
breaks.

```css
p { max-width: 66ch; }
```

`ch` is the width of the `0` glyph — self-adjusting to the actual font.

**Line height.** 1.5–1.7 for body text. Tighter as text gets bigger:
display headings want 1.0–1.2. Line height and measure move together —
longer lines need more leading to find the next line.

**Size and scale.** Pick a ratio and generate sizes from it rather than
choosing each one. 1.25 (major third) is safe; 1.333 or 1.5 for more
drama.

```css
:root {
  --step--1: 0.8rem;  --step-0: 1rem;   --step-1: 1.25rem;
  --step-2: 1.563rem; --step-3: 1.953rem; --step-4: 2.441rem;
}
```

Body copy at 16–20px. Under 16px on mobile triggers zoom in some
browsers and is hostile to older eyes regardless.

**Fluid type without media queries.** `clamp(min, preferred, max)`:

```css
h1   { font-size: clamp(2rem, 6vw, 4.5rem); }
body { font-size: clamp(1rem, 0.95rem + 0.25vw, 1.125rem); }
```

Use `rem` in the preferred term, not pure `vw`, or text stops responding
to the user's browser zoom — an accessibility failure.

**Pairing.** Two families is plenty; three needs a reason. What works:
one high-contrast serif for display + one neutral sans or serif for body +
optionally a mono for labels and numbers. What fails: two fonts from the
same category with similar proportions — they read as a mistake rather
than a pairing.

**The details that signal care:**

```css
h1, h2 { text-wrap: balance; }        /* no orphaned single word on line 2 */
p      { text-wrap: pretty; }         /* better rag, avoids short last lines */
.num   { font-variant-numeric: tabular-nums; }  /* numbers in columns align */
body   { -webkit-font-smoothing: antialiased; hanging-punctuation: first; }
```

Real quotes and dashes: `"` `"` `'` `'` `—` `–` `…`, not `"` and `--`.
Non-breaking spaces before units and after short prepositions. `&shy;`
for the one long word that breaks a mobile layout.

**Letter-spacing:** tighten large display type slightly (`-0.02em`),
open up all-caps and small labels a lot (`0.1em`–`0.3em`). Never
letter-space lowercase body copy.

---

## 2 · Space

Space is what most amateur design lacks, and it's free.

**One spacing scale, geometric, no exceptions.** 4px base, doubling:
4, 8, 12, 16, 24, 32, 48, 64, 96, 128. If a value isn't on the scale, you
don't get to use it.

**Proximity encodes relationship.** The gap between a label and its input
must be visibly smaller than the gap to the next field, or the eye can't
group them. Most confusing forms are just uniform spacing.

**Space between sections should be larger than you think** — 2–4× your
largest in-section gap. Generous section spacing is the single clearest
"this was designed" signal.

**Use logical properties** so the same CSS works in right-to-left
languages:

```css
.card { margin-block: 2rem; padding-inline: 1.5rem; }
```

**Own the vertical rhythm with the owl, not with per-element margins:**

```css
.flow > * + * { margin-block-start: 1em; }
```

Every child gets space from its predecessor; nothing gets a stray leading
or trailing margin that collapses unpredictably.

---

## 3 · Color

**Fewer colors, more values.** One accent, one neutral ramp, and
semantic colors only where meaning requires them. Most well-designed
pages are a greyscale with one hue used sparingly.

**Neutrals should not be pure grey.** Tint them toward your accent — warm
greys with warm accents, cool with cool. `#0A1210` (a dark with a green
cast) reads as intentional; `#111111` reads as unset.

**Work in a perceptual space.** `oklch(lightness chroma hue)` is now
broadly supported and behaves the way your eye expects: change lightness
and chroma stays put, change hue and brightness doesn't jump. Generating a
ramp in OKLCH gives you steps that are perceptually even; generating one
in hex or HSL does not.

```css
:root {
  --accent-400: oklch(72% 0.14 62);
  --accent-500: oklch(64% 0.15 62);
  --accent-600: oklch(55% 0.15 62);
}
```

**Contrast is a hard requirement, not a preference.** WCAG 2: 4.5:1 for
body text, 3:1 for large text (≥24px, or ≥19px bold) and for UI component
boundaries. Check it; do not eyeball it. Light grey on white is the most
common accessibility failure on the web and it is always a choice
somebody made because it looked "soft."

**Never encode meaning in hue alone.** Roughly 1 in 12 men has some form
of color vision deficiency. Pair color with a label, an icon, a weight
change, or a position.

**Dark mode is not inverted light mode.** Pure white on pure black
vibrates (halation). Use an off-white on a dark grey-with-a-cast, reduce
saturation of accents, and reduce shadow reliance in favor of subtle
borders and lighter surfaces.

```css
@media (prefers-color-scheme: dark) { :root { /* … */ } }
:root[data-theme="dark"]  { /* explicit toggle must win */ }
:root[data-theme="light"] { /* both directions */ }
```

---

## 4 · Hierarchy

Someone should be able to squint at the page — or see it at thumbnail size
— and still know what it's about and what to do.

Rank your content ruthlessly: exactly one primary element per screen. Then
express the ranking with **size, weight, color, space, and position**,
in that order of strength. Using all five at once on the same element is
shouting; two is usually right.

**One primary action per view.** Two buttons of equal visual weight is
two primary actions, which is none. Secondary actions get lighter
treatment — ghost buttons, text links, smaller size.

**Alignment creates structure.** Every element should align to something.
Optical alignment beats mathematical alignment when they disagree: a round
shape or a quotation mark needs to overhang slightly to *look* aligned.

**Sections with one job each.** For any content block, name in one
sentence the single thing it must accomplish. If you can't, the section is
doing two jobs and should be two sections — or one of the jobs isn't real.
Write that sentence in a comment above the markup; it survives the
redesign.

---

## 5 · Motion

Motion should explain a state change, not announce itself.

**Durations:** 150–250ms for small state changes (hover, focus, toggle).
250–400ms for entrances and layout changes. Over ~500ms only for a
deliberately cinematic moment. Anything animating on every scroll event
should be nearly imperceptible.

**Easing carries most of the character:**
- `ease-out` for entrances — fast start, gentle settle. Feels responsive.
- `ease-in` for exits.
- `cubic-bezier(0.2, 0.7, 0.2, 1)` — a good general-purpose "expensive"
  curve: quick departure, long confident settle.
- Never `linear`, except for continuous rotation or a progress bar.

**Animate only `transform` and `opacity`** where you can. Everything else
drags layout or paint into every frame (`INTERNET-SCIENCE.md`).

**Respect the preference, and mean it:**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

Reduced motion should still deliver the *information* — a static final
frame, an instant state change. Never a blank space where content was
going to fade in.

**The trap of scroll-triggered reveals:** they must be a progressive
enhancement. Hide with a class a script adds, never in the base CSS:

```css
.js .rv          { opacity: 0; transform: translateY(22px); transition: … }
.js .rv.on       { opacity: 1; transform: none; }
```

Get this backwards and a failed script request leaves a blank page — and
that is what crawlers and JS-disabled users see.

**Keep one steady element among moving ones.** Motion reads as meaningful
only against a constant. All-moving is noise.

---

## 6 · Accessibility

Not a checklist bolted on at the end. It's mostly the result of using the
platform correctly.

**Semantic HTML first.** `<button>` for actions, `<a href>` for
navigation, one `<h1>`, headings in order without skipping, `<nav>`,
`<main>`, `<footer>`, real `<label for>` on every input. A `<div
onclick>` is not a button: no keyboard access, no role, no focus, no
announcement. Every ARIA attribute you add is a small admission that the
element was wrong.

**Keyboard:** everything reachable by Tab, in a logical order, with a
visible focus indicator. `:focus-visible` gives you the modern behavior —
visible for keyboard users, not for mouse clicks:

```css
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
```

Never `outline: none` without a replacement.

**Images:** `alt` describing the *function* in context. Decorative images
get `alt=""` — empty, not missing, so screen readers skip them instead of
reading a filename.

**Targets:** 44×44px minimum for anything tapped.

**Don't disable zoom.** `maximum-scale=1` or `user-scalable=no` in the
viewport meta is a straightforward hostility to anyone with imperfect
vision.

**Test cheaply:** unplug the mouse and use the page. Tab through it. Run
axe DevTools or Lighthouse. Turn on the OS screen reader for five
minutes — VoiceOver (Cmd+F5), NVDA, or Narrator. That five minutes finds
more than an hour of reading guidelines.

---

## 7 · Layout, in the modern platform

Most layout problems are solved and the solutions are boring now.

```css
/* Responsive grid, no media query, no breakpoint math */
.grid { display: grid; gap: 1.5rem;
        grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr)); }

/* Center something with a max width and gutters, once, globally */
.wrap { width: min(100% - 3rem, 70ch); margin-inline: auto; }

/* Push a footer to the bottom regardless of content height */
body   { min-height: 100dvh; display: grid; grid-template-rows: auto 1fr auto; }
```

- **`dvh` not `vh`** on mobile — `vh` ignores the collapsing browser
  chrome and causes the classic "content cut off at the bottom of the
  phone" bug. `svh`/`lvh` when you specifically want the small or large
  extreme.
- **Container queries** (`@container`) let a component respond to its
  *own* width rather than the viewport's. This is what makes a card
  genuinely reusable in a sidebar and in a full-width grid.
- **`aspect-ratio`** replaces every padding-hack ratio box.
- **`:has()`** is a parent selector, and it is real:
  `.card:has(img) { … }`.
- **`min()`, `max()`, `clamp()`** eliminate most breakpoints entirely.
  Design for a continuous range, not for four fixed device widths.

**Mobile first, and honestly:** write the small-screen layout as the base
and add complexity upward with `min-width` queries. Most traffic is
mobile, most design happens on a 27-inch monitor, and that gap is where
broken pages come from. Test at 320px wide and with a 200% browser zoom.

---

## 8 · The self-review, before it ships

- [ ] Every size, space, and color comes from the declared scale
- [ ] Measure is 45–75 characters at every breakpoint
- [ ] Squint test: one obvious primary element and one primary action
- [ ] Contrast checked with a tool, not an eye — 4.5:1 body, 3:1 large
- [ ] Tab through the whole page; focus always visible and logical
- [ ] Works at 320px wide, and at 200% zoom
- [ ] Works with JavaScript disabled (content visible, links work)
- [ ] `prefers-reduced-motion` delivers the same information, statically
- [ ] Every image has intentional `alt` and explicit width/height
- [ ] Dark mode designed, not inverted — and the toggle wins over the OS
- [ ] No layout shift after load (watch it on a throttled connection)
- [ ] Real typography: curly quotes, em dashes, tabular figures in tables

---

## Sources worth returning to

- **MDN Web Docs** — the platform reference, and it's CC-licensed.
- **Refactoring UI**, Wathan & Schoger — the most directly applicable
  design book for developers.
- **Practical Typography**, Matthew Butterick — free online, opinionated,
  correct.
- **Every Layout**, Bell & Hall — layout as a small set of composable
  primitives; changes how you think about CSS.
- **Inclusive Components**, Heydon Pickering — accessible component
  patterns, free online.
- **WCAG 2.2 / WAI-ARIA Authoring Practices** — the normative source when
  something is genuinely in question.
- **Utopia.fyi** — generates fluid type and space scales as `clamp()`
  values.

*Platform features cited (`text-wrap: balance`, `oklch()`, `@container`,
`:has()`, `dvh`) are broadly supported as of 2026-07 — check
`caniuse.com` for anything you're shipping to a fixed browser floor.*
