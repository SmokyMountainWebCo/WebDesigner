# library/ — what graduated

Curated substance extracted from real pages. Everything in here cleared
the provenance and license gate in `docs/INTAKE.md`; nothing here is a
copied file.

```
palettes/   colors as OKLCH + hex, banded, with what they were doing
tokens/     ready-to-paste :root blocks — spacing, type, color scales
patterns/   a technique written up: problem, code, cost, fallback
shaders/    scene fragments plus the phase-gating math and knob notes
snippets/   small self-contained HTML/CSS worth pasting again
```

## Every entry carries a header

No header, no entry. Four facts, at the top of the file:

```
Source:  where it came from (URL, or "original")
License: the terms it's usable under, or "n/a — measurements only"
Date:    when it was recorded
What:    one line on what it is and when to reach for it
```

For a pattern or a palette derived purely from *measuring* a page, the
license line is `n/a — measurements only`: a color value and a technique
aren't copyrightable, which is exactly why those are the things that
graduate. For anything that includes actual bytes from somewhere else —
a font, an SVG, a code fragment — the license must name real terms.

## What belongs here vs in docs/

A `library/` entry is a **specimen**: one palette, one pattern, one shader,
kept because you'll reach for it again.

A `docs/` pack is a **generalization**: the rule that holds across
specimens.

When the same pattern turns up three times, promote it — write the
paragraph in the relevant pack and leave the specimens here as the
evidence. That promotion is the point of the whole intake pipeline.

## Keep it small

Twelve entries you reuse beats four hundred you don't. Prune anything you
haven't reached for; the harvest reports can always regenerate a candidate
list from the raw drops.
