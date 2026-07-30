# Intake — turning a pile of saved pages into substance

> **Owns:** the pipeline that absorbs saved `.html` files and `.zip`
> archives and turns them into technique this repo can use — the commands,
> the provenance and license gate, the scrub rules, and what may graduate
> into `library/`.
> **Not here:** what the extracted measurements *mean* (`DESIGN.md`,
> `INTERNET-SCIENCE.md`). How to build with them (`tools/README.md`).

A folder of saved pages is raw ore. It contains real answers to real
questions — what palette that page actually used, how it embedded its
fonts, which platform features it leaned on, how heavy it really was — and
those answers are worth more than any amount of guessing. This is the
process for getting them out without dragging in anything that shouldn't
travel.

---

## The three commands

```bash
mkdir -p intake                       # drop .html files and .zip archives here
python3 tools/ingest.py  intake/ -o _work/
python3 tools/harvest.py _work/manifest.json -o _work/harvest
# then read _work/harvest/REPORT.md
```

**`intake/` and `_work/` are gitignored on purpose.** Raw drops never get
committed — see the gate below. What gets committed is the curated result
in `library/`, and only after it clears the gate.

### 1 · `ingest.py` — unpack and inventory

Answers *what did I actually drop in.* Walks the folder, safely extracts
every `.zip`, hashes every file, collapses duplicates by content, and
writes `_work/manifest.json`.

Archives from anywhere are hostile input, so extraction refuses — rather
than sanitizes — path-traversal entries (`../../etc/…`), absolute paths,
symlinks and device nodes, entries over the compression-ratio ceiling
(zip bombs), and anything that would push an archive past
`--max-bytes` uncompressed. Refusals are listed in the summary and in
`manifest.json`; the rest of the archive still extracts.

Only `.zip` is unpacked. Other archive formats are reported and skipped —
extract them by hand first, so you see what you're expanding.

### 2 · `harvest.py` — extract the transferable part

Answers *what's in here worth keeping.* Per page it pulls:

| Category | What comes out |
|---|---|
| **Palette** | Every color, normalized to hex, ranked by use, split into dark/mid/light bands. Counts of `rgb()`, `hsl()`, `oklch()` forms |
| **Tokens** | Every CSS custom property and its value — somebody else's design system, stated |
| **Scales** | Every `font-size` and every spacing value, sorted and frequency-ranked. A tight repeating set is a real scale; a long tail means there wasn't one |
| **Fonts** | `@font-face` families, weights, styles, formats, and crucially whether each is a `data:` URI or an external fetch |
| **Techniques** | ~48 platform features detected — grid, `clamp()`, `:has()`, container queries, OKLCH, `backdrop-filter`, `content-visibility`, scroll-driven animation, WebGL, `<dialog>`, and so on |
| **Flags** | Things this repo has opinions about: `px` font sizes, `100vh`, `outline:none`, disabled zoom, `!important`, float layout, `document.write` |
| **Dependencies** | Every external origin the page fetches from — each one a request, a cache entry, a privacy exposure, and a future failure |
| **Shaders** | Inline GLSL: size, uniform names, whether it uses noise and `smoothstep`, loop count |
| **Distribution** | Title, description, `robots`, the Open Graph and Twitter tag sets, JSON-LD `@type`s |
| **Accessibility** | `lang`, alt coverage, images with explicit dimensions, heading level skips, labelled inputs, whether zoom is disabled |
| **Weight** | Total bytes split into markup, inline CSS, inline JS, linked CSS/JS, and base64 payload; whether the page is fully self-contained |
| **Linked** | Which local stylesheets and scripts were folded in, and any local reference that couldn't be resolved |

Output: one JSON per page, a `corpus.json`, and `REPORT.md` — a
corpus-wide roll-up that ranks the palette, shows technique adoption as a
bar per feature, lists every external origin, and ends with a
**Candidates to graduate** section.

Run it on a single file without a manifest when you just want to read one
page:

```bash
python3 tools/harvest.py some-page.html | less
```

### 3 · Read the report, then graduate what earns it

The report is a *proposal*, not a result. Nothing moves until you decide
it should, and nothing moves without provenance.

---

## The gate — what may graduate, and what never does

This repo's premise is that it carries **general technique and nothing
else** (`CLAUDE.md`). Intake is the one place where material from outside
arrives, so it's the one place that needs a rule with teeth.

### Graduates freely — measurements and method

- **Numbers**: palette values, scale steps, weights, byte counts, ratios.
- **Method**: that a page gated its scene phases with `smoothstep`, that
  it embedded fonts as base64, that it used a 13× hashed grid. The
  *approach*, written in your own words.
- **Platform findings**: which features are in real-world use, what broke,
  what a technique cost in bytes.
- **Your own work**: anything you wrote is yours to move.

### Never graduates

- **Copy.** Headlines, body text, taglines, anything written to persuade.
  `harvest.py` deliberately does not extract it.
- **Images, video, audio.** Almost always licensed to whoever made the
  page.
- **Names.** People, companies, addresses, phone numbers, prices, and
  anything identifying a client or a prospect.
- **Fonts you don't have a license for.** See below — this is the one that
  carries real exposure.
- **Whole files.** A saved page copied into the repo is not technique,
  it's redistribution.

### The provenance requirement

`ingest.py` writes two deliberately empty fields on every manifest entry:

```json
"source_url": null,
"license": null
```

**Fill them in by hand for anything you intend to graduate.** If you can't
say where a file came from and under what terms, it doesn't move. That's
not bureaucracy — reconstructing provenance a year later is genuinely
impossible, and "I found it in a folder" is not a license
(`OPEN-SOURCE.md`).

### The font trap specifically

`harvest.py` reports embedded faces, and `extract_fonts.py` will happily
recover them from any page that has them. **That is a capability, not a
permission.** A recovered `@font-face` may be:

- **OFL** (nearly every open font) — reusable, including commercially,
  and renaming is required only if you modify it. Fine.
- **A commercial webfont license** — typically bound to a domain or a
  pageview count, and non-transferable. Extracting it and using it
  elsewhere is straightforward infringement.
- **Unknown** — treat as commercial until proven otherwise.

Identify the family, find it on Google Fonts or Fontsource; if it's there
under OFL, **download the legitimate copy** rather than shipping the one
you extracted. If it isn't, it doesn't travel. The extracted version is a
useful way to *identify* a face and to study how it was subset and
embedded, and that's where it stops.

---

## Where graduated substance lands

```
library/
  palettes/     One file per palette. Colors as OKLCH plus hex, banded,
                with a note on what they were doing and where they came from.
  tokens/       Custom-property sets worth reusing — spacing, type, color
                scales as ready-to-paste :root blocks.
  patterns/     A technique written up: what problem, what code, what it
                cost, what it degrades to, where it came from.
  shaders/      Scene fragments and the phase-gating math, with the knob
                notes that make them reskinnable.
  snippets/     Small, self-contained HTML/CSS you'd actually paste again.
```

Every file in `library/` carries a short header: **what it is, where it
came from, its license, and the date.** No header, no entry — the same
rule as everything else here.

When a pattern shows up three times across the corpus, it stops being a
snippet and becomes a paragraph in one of the `docs/` packs. That's the
loop this whole pipeline exists to feed: raw drops → measurements →
candidates → a written-up pattern → a doc that makes the next build
faster.

---

## Known limitations, honestly

The harvester is regex over markup and CSS. It's fast, it needs no
dependencies, it never executes anything — and that buys it these blind
spots:

- **Stylesheets from other origins aren't fetched.** Harvest reads the
  page's own folder — including the `Page Title_files/` sidecar a browser
  writes on "Save Page As → Complete", which is where a saved page keeps
  every color, token, and technique — plus one level of `@import`. It
  never goes to the network. A page whose CSS is on a CDN and wasn't
  saved alongside it will report that href under `linked.unresolved` and
  harvest thin; save the page complete, or fetch the stylesheet into the
  folder yourself. `--no-follow` turns the whole behavior off.
- **JS-rendered pages yield only the shell.** Anything a framework paints
  at runtime isn't in the saved markup, which is the same reason crawlers
  miss it (`MASTERING-THE-INTERNET.md`).
- **Templates read as broken.** A page with `{{TOKEN}}` placeholders will
  report invalid JSON-LD and odd token values — it's an un-substituted
  template, not a bug in the page. Harvest the *built* output when you
  have it.
- **Minified CSS harvests fine, but attribution suffers.** You get the
  values without the structure that explains them.
- **Technique detection is presence, not correctness.** "Uses
  `backdrop-filter`" doesn't mean it used it well, and the flags are
  prompts to look, not verdicts.
- **No visual check.** Nothing here tells you whether a page looked good.
  For that, open it, or run `tools/check.js` against something you built.

---

## The habit that makes this pay off

Drop everything in and run the pipeline whenever the pile grows — it costs
seconds and it's non-destructive. But **graduate deliberately, in small
amounts.** A `library/` with twelve entries you actually reuse is worth
more than four hundred extracted fragments nobody reads, which is the
failure mode every clippings folder ever has had.

The report's **Candidates to graduate** section is ranked for exactly this
reason: work the top of the list, ignore the rest until it matters.
