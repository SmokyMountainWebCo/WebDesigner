# Night ridge — a dark palette that carries one accent

    Source:  original
    License: n/a — measurements only
    Date:    2026-07-30
    What:    A near-black ground with two low-chroma neutrals and one warm
             accent. Reach for it when a dark page needs to feel like a
             place rather than a dashboard.

## The values

| Role | Hex | OKLCH | L | Job |
|---|---|---|---|---|
| ground | `#0A1210` | `oklch(17.3% 0.013 177.5)` | 0.17 | page background; nearly neutral, faintly green |
| raised | `#101C17` | `oklch(21.3% 0.020 166.7)` | 0.21 | panels and cards, one step up from ground |
| text | `#EDE6D8` | `oklch(92.7% 0.020 84.6)` | 0.93 | body; warm off-white, never `#fff` |
| muted-cool | `#93A7B4` | `oklch(71.7% 0.029 236.4)` | 0.72 | secondary text, labels |
| muted-warm | `#7E8F89` | `oklch(63.5% 0.022 172.4)` | 0.63 | tertiary text, captions |
| **accent** | `#E9A63C` | `oklch(77.2% 0.141 74.7)` | 0.77 | links, focus rings, prices, one CTA |
| accent-soft | `#E8B98A` | `oklch(81.7% 0.082 66.2)` | 0.82 | italic emphasis, eyebrow text |
| accent-alt | `#9BBD7E` | `oklch(75.8% 0.094 131.4)` | 0.76 | confirmations, checkmarks only |

Hairlines are the cool neutral at low alpha — `rgba(147,167,180,.22)` —
not a lighter grey. A hairline made from the text color reads as a scratch;
one made from the muted color reads as an edge.

## Why it holds together

**Chroma is the whole trick.** Every neutral sits between 0.013 and 0.029
chroma — technically colored, perceptually grey. The accent jumps to 0.141,
roughly 5× anything else. That gap is why a single amber element commands
a whole dark screen without being loud; nothing else on the page competes
for saturation.

**The lightness ladder does the structure.** 0.17 → 0.21 for
ground → raised is a barely-there step, and that's deliberate: panels
separate by their hairline border, not by contrast. Text lands at 0.93 —
against `#0A1210` that's about **15.6:1**, far past the 4.5:1 floor, which
is what lets the muted tones drop to 0.63 and still pass on body-size text.

**Warm text on cool ground.** The off-white carries hue 84.6 (warm) while
the ground carries 177.5 (cool-green). Opposing temperature is what stops
a dark theme reading as an unstyled dark mode.

## Using it

Cap the accent at roughly one element per viewport. The moment two amber
things are on screen together, neither is the thing being pointed at — and
the palette's entire load-bearing structure is that gap in chroma.

Check any new color against the ladder before adding it: if its chroma
lands between 0.03 and 0.13 it will read as a muddy accent, neither
neutral nor deliberate. Push it to one side or the other.
