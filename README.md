# WebDesigner

An open knowledge base for building things on the web: how the internet
actually works, how to make pages that look expensive and load fast, which
free and open-source parts to build them from, and how to get them found.

No client work, no strategy, no names. Everything here is general
technique — portable to any project, any market, anybody.

## The structure

Knowledge packs and a working toolchain. The packs are the *why* and the
*what*; `tools/` and `template/` are the *how*, runnable today.

```
docs/
  INTERNET-SCIENCE.md        How the internet works: DNS, TCP, TLS, HTTP,
                             CDNs, caching, the browser rendering path.
  MASTERING-THE-INTERNET.md  Distribution: crawling, indexing, structured
                             data, link previews, feeds, measurement.
  DESIGN.md                  Fundamentals: type, scale, color, space,
                             hierarchy, motion, accessibility.
  DESIGN-LOOPHOLES.md        Techniques with disproportionate payoff —
                             cheap moves that read as expensive.
  OPEN-SOURCE.md             The free stack: licenses, fonts, icons,
                             images, data, hosting, self-hosting.
  SCROLL-SCENE.md            One deep case study: a scroll-driven WebGL
                             background in ~90 lines of shader.
  DNS-RUNBOOK.md             Pointing domains without taking a business
                             offline or killing its email.
  INTAKE.md                  Absorbing saved pages and zip archives into
                             technique — the pipeline and the license gate.
  BUILD-PROTOCOL.md          The order of operations for every build, and
                             the automated gate before deploy.
  CINEMATIC-SCROLL.md        Scroll as camera: video scrub, image sequences,
                             photogrammetry and Gaussian splats — and which
                             one a given trade actually needs.
template/
  page-template.html         A single-file page: embedded fonts, inline
                             CSS/JS, scroll-driven shader, zero requests.
  config.example.json        Sample values for every {{TOKEN}}.
  fonts.css.example          The format the build expects for embedded fonts.
tools/
  build.py                   config + fonts + template -> one HTML file.
  extract_fonts.py           Pull embedded @font-face rules out of any page.
  check.js                   Headless QA: console errors, WebGL alive,
                             screenshots at three scroll depths.
  ingest.py                  A drop folder of .html/.zip -> safe unpack,
                             hash, de-duplicate, inventory.
  harvest.py                 Saved pages -> palette, tokens, scales, fonts,
                             techniques, dependencies, shaders, a11y, weight.
  preflight.py               The gate: refuses to ship a build with unfilled
                             blanks, broken previews or a dead canonical.
  distinct.py                Across a set of sites: how alike the copy,
                             structure, headlines and assets really are.
  network-policy.example.json  The four thresholds distinct.py reads.
library/                     What graduated: palettes, tokens, patterns,
                             shaders, snippets. Specimens, each with a
                             source and a license.
```

## Feeding it

The repo is built to absorb material. Drop saved pages and archives into
`intake/` and run two commands:

```bash
python3 tools/ingest.py  intake/ -o _work/
python3 tools/harvest.py _work/manifest.json -o _work/harvest
# read _work/harvest/REPORT.md
```

You get a corpus report: the palette ranked across every page, technique
adoption per feature, every external origin depended on, the type and
spacing scales actually used, inline shaders with their uniforms, and a
ranked **Candidates to graduate** list.

`intake/` and `_work/` are gitignored. What gets committed is the curated
result in `library/`, and only after it clears the provenance and license
gate in `docs/INTAKE.md` — measurements and method travel, copy and
licensed assets do not.

## Where to start

| If you want to… | Read |
|---|---|
| understand what happens between a keystroke and a painted pixel | `docs/INTERNET-SCIENCE.md` |
| get a page indexed, previewed, and measured | `docs/MASTERING-THE-INTERNET.md` |
| make something look considered instead of assembled | `docs/DESIGN.md` |
| get a big visual return for very little code | `docs/DESIGN-LOOPHOLES.md` |
| build without paying for anything, legally | `docs/OPEN-SOURCE.md` |
| ship a page that never breaks from a dead CDN | `template/` + `tools/` |
| point a domain at a site | `docs/DNS-RUNBOOK.md` |
| turn a folder of saved pages into reusable technique | `docs/INTAKE.md` |
| build a scroll-driven tour, flyover or walkthrough | `docs/CINEMATIC-SCROLL.md` |
| start a new build, or build forty at once | `docs/BUILD-PROTOCOL.md` |

## The principles the whole repo runs on

1. **One file, no dependencies, where you can get away with it.** Fonts as
   base64 woff2, CSS and JS inline. The page can be emailed, hosted
   anywhere, opened from a thumb drive in ten years, and never breaks
   because a CDN went dark or an npm package was unpublished.
2. **Works without JavaScript, then better with it.** Content is in the
   HTML. Enhancement hides or animates things only after a script sets a
   class. A page that shows nothing until a bundle parses is broken for
   crawlers, slow connections, and anyone whose script request failed.
3. **Degrade visibly, never silently.** A WebGL shader that fails to
   compile hides its canvas and reveals a CSS gradient. A missing font
   falls back to a stack that was chosen, not defaulted.
4. **Measure before optimizing.** Back-of-the-envelope math first, then
   the simplest design that meets the number. Most pages are slow for one
   or two identifiable reasons, and neither is usually the framework.
5. **Respect the user's stated preferences.** `prefers-reduced-motion`,
   `prefers-color-scheme`, and keyboard focus are not edge cases; they are
   the operating system telling you what this person needs.
6. **Cite the source and date it.** Web platform behavior changes. A
   technique with a date attached can be re-checked; one without becomes
   folklore.

## What "loopholes" means here

Not tricks that cheat a user or a search engine — those get penalized,
break, or both. A loophole in this repo is a **leverage point**: a place
where the platform gives you a large effect for a small, honest input.
One CSS property that replaces a JavaScript library. A gradient that
replaces a photograph. A fragment shader that replaces a video file. A
single well-formed meta tag that changes how a link looks everywhere it
gets pasted.

The test is: *does this hold up if the user reads the source?* If yes,
it's technique. If no, it's a bug waiting to be filed.
