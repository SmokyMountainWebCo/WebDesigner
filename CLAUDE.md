# CLAUDE.md

This is an **open knowledge base for building on the web** — how the
internet works, how to design for it, which free and open parts to build
from, and how to get the result found.

**It carries no business substance.** No clients, no prospects, no
strategy, no pricing, no names, no proprietary material. If a task would
add any of those, it belongs in a different repo. Everything here must be
general technique that would be equally true and useful for anyone.

## What to read, by task

Each doc's role header (the `Owns:` / `Not here:` block under its title) is
the authority on its scope — this table just routes you there.

| If the task is… | Read |
|---|---|
| performance, latency, caching, protocols, rendering | `docs/INTERNET-SCIENCE.md` |
| indexing, crawlers, structured data, link previews, feeds, measurement | `docs/MASTERING-THE-INTERNET.md` |
| type, color, space, hierarchy, motion, accessibility | `docs/DESIGN.md` |
| getting a big visual result cheaply; what technique to reach for | `docs/DESIGN-LOOPHOLES.md` |
| licenses, fonts, icons, images, data, hosting, self-hosting | `docs/OPEN-SOURCE.md` |
| the scroll-driven WebGL background, in detail | `docs/SCROLL-SCENE.md` |
| pointing a domain, moving a site, not killing anyone's email | `docs/DNS-RUNBOOK.md` |
| building or shipping an actual page | `tools/README.md`, then `template/` |

## House rules

- **One invariant core, no forks.** A document with variable blocks beats
  six copies of that document — copies drift out of sync within a year.
  If two sections would say nearly the same thing, they're one section.
- **Every section has exactly one job.** Name it in a sentence in a
  comment above the markup or under the heading. If it takes two
  sentences, it's two sections — or one of the jobs isn't real.
- **Cite the source and date the claim.** Web platform behavior, Core Web
  Vitals thresholds, browser support, and license terms all change. A
  number with an as-of date can be re-checked; one without becomes
  folklore. Every doc here ends with its sources and a date stamp — keep
  that habit when editing.
- **Verify before asserting.** Don't claim a feature is supported without
  checking `caniuse.com`; don't claim a page is fast without a throttled
  measurement; don't claim a link works without loading it. Run
  `tools/check.js` before saying a built page is done.
- **Prefer the platform to a dependency.** Check MDN before adding a
  library. `:has()`, `<dialog>`, container queries, `clamp()`, scroll-driven
  animations, and OKLCH all moved from library to built-in recently, and
  more will.
- **Every technique must degrade visibly.** A shader that fails reveals
  the gradient beneath it; a font that fails falls back to a chosen stack;
  a script that fails leaves readable content. "What happens when this
  fails?" is the question that separates a technique from a liability — if
  the answer is "blank page," it doesn't ship.
- **Progressive enhancement is not optional.** Content lives in the HTML.
  Scripts hide and animate things only after setting a class. A page that
  shows nothing until a bundle parses is broken for crawlers, for slow
  connections, and for anyone whose request failed.
- **Accessibility is a requirement, not a section.** Semantic elements,
  4.5:1 contrast on body text, visible focus, keyboard reachability,
  honored `prefers-reduced-motion`. These are correctness, not polish.
- **Soft-word anything legal.** Licenses and compliance are summarized
  here by a developer, not a lawyer — possibilities to verify, never
  advice.
- **No dark patterns, and no gaming anything.** "Loophole" in this repo
  means a leverage point the platform genuinely offers, and the test is
  whether it holds up when someone reads the source. Cloaking, hidden
  text, invisible structured data, and bought links are all out — they're
  detectable, they get penalized, and they're more work than the thing
  that works.

## Working in the repo

Runnable assets are meant to stay runnable. After touching `template/` or
`tools/`, prove the chain still works before committing:

```bash
python3 tools/build.py template/page-template.html \
    -c template/config.example.json -o /tmp/page.html
node tools/check.js /tmp/page.html      # expects PASS
```

`dist/` output and generated screenshots are build artifacts — don't commit
them.
