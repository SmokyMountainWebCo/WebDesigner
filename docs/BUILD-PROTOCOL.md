# Build protocol — the order of operations for every site

> **Owns:** the sequence run before, during and after every build — how
> the field is determined, what facts must exist before code is written,
> and the gate a build has to clear before it deploys.
> **Not here:** how to make it look good (`DESIGN.md`,
> `DESIGN-LOOPHOLES.md`). How to make it fast (`INTERNET-SCIENCE.md`).
> How to get it found (`MASTERING-THE-INTERNET.md`).

Seven phases. Each ends in something checkable, and **phase 4 is
automated** — `tools/preflight.py` exits non-zero, so the protocol holds
whether one site is being built or forty.

**Every rule below exists because the failure it prevents actually
happened.** Nothing here is a best-practice list copied from elsewhere.

---

## Phase 0 · Determine the field

Before anything: **what question does the visitor arrive with, and what
do they do once it's answered?** Everything downstream is a consequence.

| Archetype | Arrives asking | Owes them | Schema type | The next step |
|---|---|---|---|---|
| **service** | *Can you fix this, and can you come now?* | Reachability, proof of licence, service area | `Plumber`, `Electrician`, `LocalBusiness`… | a click-to-call link |
| **lodging** | *What is it actually like there?* | Rooms, the space, dates | `LodgingBusiness`, `VacationRental` | a booking or availability action |
| **venue** | *What's on, and what's it like in the room?* | Lineup, hours, the space | `EventVenue`, `Restaurant` | tickets, menu or hours |
| **listing** | *What is this property and what does it cost?* | Facts, figures, photographs | `RealEstateListing` | a way to enquire |
| **index** | *Who's in this, and can I trust the list?* | Coverage and its rules | `CollectionPage`, `ItemList` | into a member's own site |
| **info** | *What is this?* | A straight answer | — | — |

**The archetype is an argument to the gate**, not a note in a doc:
`--archetype service` makes a missing `tel:` link a **blocking failure**,
because a plumber's site that doesn't offer a phone number has failed at
the only job it had.

### Same core, different dialect

Across a set of sites the **core is invariant** — palette discipline, type
scale, scroll grammar, degradation behavior, the gate. The **dialect** is
what changes per field: which question gets answered above the fold, what
the primary action is, what proof carries weight (a licence number for a
trade, photographs for lodging, a lineup for a venue), and where motion is
worth its bytes.

One core with marked variable blocks, never a fork per trade. Six copies
of a template drift apart within a year; one template with dialect slots
does not.

---

## Phase 1 · The facts contract

**Do not start until the facts that cannot be invented are in hand.** This
is the phase that gets skipped, and skipping it is what produces a
finished-looking site that can never launch.

*Observed: a paid, "ready" site sat undeployable holding **19 unfilled
placeholders** — licence number, email, hours, service radius, warranty
terms — while its own README claimed going live was two deletions.*

Per archetype, the non-inventable minimum:

- **service** — legal business name, phone, **licence number**, insurance
  status, service radius, hours, emergency policy, warranty terms.
- **lodging** — address, sleeps/bed/bath, amenities, permit status,
  cancellation policy, **real photographs**, booking method.
- **venue** — address, hours, capacity, lineup or menu source, ticketing.
- **listing** — address, price, acreage/square footage, permit or zoning
  status, disclosures, photographs.

Three rules that keep this phase honest:

1. **Mark every blank in a form a machine can find.** House convention is
   `⟨angle brackets⟩`. The gate greps for them — an unmarked blank is one
   that ships.
2. **A blank is never filled with a plausible guess.** No invented hours,
   no rounded licence numbers, no stock review counts. If it isn't
   supplied, it stays a marked blank and the page doesn't launch.
3. **Blanks go on the invoice, not in the backlog.** The contract names
   what's outstanding and who owes it. A build blocked on the client is
   fine; a build blocked on the client that nobody told the client about
   is not.

---

## Phase 2 · Build

Standard rules apply (`README.md` principles, `DESIGN.md`, `template/`).
Three that the gate enforces:

- **Content in the HTML.** Enhancement only after a script sets a class.
- **Absolute URLs for anything a crawler resolves** — `og:image`,
  `og:url`, `canonical`. Relative preview images silently don't work.
- **One `<h1>`, headings in order, `lang`, zoomable viewport, `alt` on
  every image.** Correctness, not polish.

---

## Phase 3 · Declare the build's status

Every build is one of two things, and it must say which:

- **Launching** — real, indexable, has to be complete.
- **Draft** — a spec build, pitch, preview or audit made for one
  recipient. Carries `noindex`, may hold marked blanks, and passes the
  gate with `--draft`.

Getting this wrong in either direction is a real failure:

*Observed: a page labelled "Concept Preview" and an audit of a third
party's website were both publicly crawlable, while a comparable named
pitch correctly carried `noindex`.*

**And the draft banner is part of the guard.** A visible "this is a
working draft" note in the body must be removed by the same act that
removes `noindex` — the gate fails a page that is indexable while still
claiming to be a draft, because that combination means somebody removed
one and forgot the other.

---

## Phase 4 · The gate

```bash
python3 tools/preflight.py site/ --archetype service --base https://the-real-host/
python3 tools/preflight.py site/ --archetype lodging --base https://host/ --draft
python3 tools/preflight.py site/ --archetype index   --base https://host/ --net
```

`FAIL` blocks and exits 1. `WARN` is ship-able but somebody chose to.
`--strict` promotes warnings to blocking. `--net` additionally checks that
the `og:` URLs actually resolve.

**What it blocks, and why each one is there:**

| Check | The failure it caught |
|---|---|
| **placeholders** | 19 unfilled blanks in a site called ready |
| **host-drift** | `canonical`, `og:url` and `og:image` naming a host that returned **404** — every share came back empty |
| **link-preview** | 4 pages with **no `og:` tags at all**, rendering as a bare grey box in every DM |
| **og-image exists** | a preview pointing at a file not in the build |
| **draft-banner** | draft language in the body of an indexable page |
| **robots** | `Disallow: /` left on a build that is launching |
| **call-to-action** | an archetype's whole job missing — no `tel:` on a trade site |
| **json-ld** | invalid or archetype-inappropriate structured data |
| **a11y** | `outline:none` with no `:focus-visible`, missing `lang`, disabled zoom, no `alt`, no `<h1>` |
| **dead-link** | an internal link with nothing behind it |
| **fonts** | megabytes of identical embedded faces duplicated across a page set |

**Precision over recall, deliberately.** An early version matched
`/your[ _]name/i` and flagged a form's `<label>Your name</label>` plus two
lines of ordinary prose. A blocking gate that cries wolf gets switched
off, so the patterns only match things that cannot be normal English.

**The gate has caught its author.** It blocked a launch bundle whose
hostname rewrite had produced `https://precisionplumbin/` — no domain —
before that bundle went anywhere.

---

## Phase 5 · Deploy, then record

1. **Confirm what's live before replacing it.** Fetch the current
   production HTML and hash it against the source you're about to build
   from. If they differ, something is live that isn't in the repo — find
   out what before overwriting it.
2. **Know how the site deploys.** A project that builds from a git branch
   must be fixed in its repo; a manual upload to a git-linked site *looks*
   fixed and is silently reverted by the next push. That's worse than not
   fixing it.
3. **Verify after deploying.** Re-fetch and hash against the intended
   build. "Deploy succeeded" is not evidence the right bytes are live.
4. **Record it.** One register: URL, archetype, launching-or-draft, paid
   or not, and what it's blocked on. *Observed: 20 deployed properties
   with the slugs scattered across five files and no record of which had
   been paid for.*

---

## Building at scale

For a development, a portfolio, or any set built at once, the protocol
changes in exactly two ways.

**One core, N dialect files.** A build is data — the facts contract as
JSON — plus the shared template. Adding site 40 adds a data file, never a
template copy. `tools/build.py` already takes this shape.

**The gate runs per site, and the exit code is the release.**

```bash
fails=0
for site in dist/*/; do
  python3 tools/preflight.py "$site" \
      --archetype "$(jq -r .archetype "$site/build.json")" \
      --base      "$(jq -r .base      "$site/build.json")" || fails=$((fails+1))
done
[ "$fails" -eq 0 ] || { echo "$fails site(s) blocked"; exit 1; }
```

---

## Phase 6 · Distinctness — the part that only fails at scale

A set of sites built from one template has a failure mode no single site
has: **templated sameness.** Forty pages sharing a headline shape with one
swapped noun read as spam to a person and to a search engine, and the set
becomes worth less than any one site in it.

The instinct is to fix it by rewriting — spinning the copy so it *reads*
different. That is the thing being penalized, it is more work than the
alternative, and it does not survive somebody reading two of the pages
side by side.

**The leverage point is that difference should be a consequence of data,
not of writing.** Four ways to get it, in order of payoff.

### 1 · Build on public data nobody else bothers to gather

This is the real loophole, and it is free. Every property and every
business sits on public facts that are *already* unique to it:

- **County parcel, permit and assessor records** — acreage, permitted
  use, year built, lot dimensions, zoning, permit history.
- **Elevation, aspect and terrain** — a ridge parcel and a valley parcel
  have genuinely different numbers.
- **FEMA flood zone, USGS water data, NOAA climate normals** — first
  frost, annual rainfall, snow days.
- **Census and DOT** — traffic counts on the access road, drive times.

A page built from its own parcel's records cannot be confused with
another, because the facts differ. It also answers questions a buyer or
guest actually has and competitors' pages do not, which is the definition
of value the policy is written around. **Cite each source on the page**;
sourced public data is exactly the "transparent sourcing" that separates
useful scaled content from abuse.

### 2 · Let facts decide which sections exist

Do not build one layout with slots. Build a **component library** and let
the data choose:

```
if facts.hot_tub:        render(hot_tub_block)
if facts.emergency_247:  render(emergency_band)
if facts.permit_number:  render(permit_provenance)
```

Then the page *shape* varies because the businesses vary, automatically
and honestly. Two cabins with different amenities get different pages
without anybody writing a second template. This is also why the facts
contract in Phase 1 pays for itself twice.

### 3 · The one thing that cannot be templated

**Photographs of the actual place.** No amount of structure or copy work
substitutes, and nothing else makes two sites unmistakably different at a
glance. If the budget allows exactly one per-site investment, this is it.

### 4 · Make the entity distinct to machines

Distinct `geo`, `areaServed`, `address`, `telephone` and `sameAs` in each
site's structured data. Cheap, and it is the difference a crawler can
read without parsing prose.

---

### Where the actual line is

The relevant policy is **scaled content abuse**, added to Google's spam
policies in March 2024 and still the governing guidance in 2026. The test
is intent and value: do the pages genuinely serve users, or do they exist
to capture traffic by volume.

**Doorway pages** are defined narrowly and specifically — multiple
domains or pages targeted at regions or cities that **funnel users to one
destination**. That definition is the thing to stay clear of, and it maps
onto this work precisely:

- **Forty sites for forty different businesses, each owned by that
  business and serving its own customers, is not doorway behavior.** The
  sites do not funnel anywhere; each is the destination. This is a
  legitimate model and it should be described that way.
- **Forty unpaid spec sites that all point back to one agency is closer
  to the line**, because the funnel is real. It may still be defensible,
  but it is worth being deliberate: keep spec builds `noindex` until the
  business owns them, and the question disappears entirely.

The safest structural answer is also the honest one: **the client owns
the site.** An owned site serving its own customers is not scaled content
under anyone's definition.

---

### A network is not the same problem as a batch

There are two different things one template can produce, and they fail in
opposite directions.

- **A batch** — unrelated sites for unrelated businesses that merely
  happen to share a builder. Nothing should tie them together. The risk
  is sameness.
- **A network** — a deliberate family, where belonging is the point: a
  registry and its members, a development and its properties. **Here the
  shared look is the asset.** The risk is that nothing signals the sites
  belong together at all.

**The rule that resolves it: shared chrome, unshared content.**

| Should be shared across the family | Must differ per site |
|---|---|
| palette, type scale, spacing ladder | every sentence |
| nav and footer grammar, the registry badge | the facts |
| structured-data shape (`isPartOf` / `memberOf` → the registry) | photographs |
| performance floor, a11y floor, failure behavior | which sections exist |
| the gate itself | the entity: `geo`, `address`, `areaServed` |

That is how a franchise, a newspaper's local editions or a hotel group
work. You recognise the brand instantly; every location carries its own
address, hours, staff and photographs. Nobody calls that spam, because
the shared part is *chrome* and the unshared part is *substance*.

**Share the chrome literally, not by copying it.** A family whose shared
layer is duplicated into every site drifts apart the first time one is
edited — and pays for the same bytes N times
(`library/patterns/embedded-fonts-break-even.md`). One cached stylesheet
served from the registry's own origin buys cohesion *and* weight at once.
The trade is a dependency on that origin: weigh it against
`README.md` principle 1, and note that a member site whose registry
stylesheet fails should still be readable — chrome is chrome.

**On cross-linking, be deliberate.** A registry that links out to its
members is a directory doing its job, and a member linking back with a
badge is normal. What is not normal is a large set of sites under one
owner cross-linking primarily to pass ranking signals. The test is the
same as everywhere else here: is the link editorial, and does the
directory have value to a reader who never clicks through?

Run the set with `--network` and the second failure mode is measured too:

```bash
python3 tools/distinct.py sites/ --network --cohesion 0.35
```

Copy overlap still blocks. Structural overlap *below* the cohesion floor
is reported as the family failing to read as one, and high shared-asset
overlap becomes a good sign rather than a suspicious one.

*Measured 2026-07-30 on a real seventeen-site set intended to become a
community: copy 0.1% (healthy), but **structure 11.8% and shared assets
1%**, with **135 of 136 pairs below the cohesion floor**. The sites do not
share so much as a font. For that set the live problem was never
templated sameness — it was that nothing tied the family together.*

### Measure it, don't assume it

Sameness is invisible from the inside — each site looks fine on its own
screen. `tools/distinct.py` measures the set:

```bash
python3 tools/distinct.py dist/ --threshold 0.30
```

Four independent signals, because they fail differently: **copy**
(8-word shingles), **structure** (block-tag 5-grams), **headings**
(reduced to sentence shape, so "Three hundred seats, one box office" and
"Thirty-nine bedrooms, one front door" register as one formula), and
**assets** by content hash.

**Read the pair, not the number.** High structure with low copy is a
design system working correctly. **High copy overlap is the failure,
whatever the structure says.** A shared font set showing 100% asset
overlap is fine; a shared hero photograph means neither site has one.

**A measured baseline, from a real seventeen-site set (2026-07-30):**

| Signal | Average over 136 pairs |
|---|---|
| copy | **0.1%** |
| structure | 11.8% |
| headings | 0.6% |

That is a healthy set — the sites are genuinely different builds, not one
build repeated. One pair of pilot previews measured **100% structural
identity with 17% copy overlap**. Read that correctly: at the default
threshold it passes, and for a deliberate network an identical skeleton is
**on-brand rather than defective**. It is the copy figure that would have
mattered, and it was fine. Heading-shape reuse across the set — the same
sentence formula appearing on two sites — is the earlier warning, and the
cheaper one to act on.

Run it before a batch ships. It exits non-zero over the threshold.

## Sources and date

Written **2026-07-30**. The checks encode failures observed in a real
twelve-page corpus and a twenty-site deployment; the thresholds
(title ~60, description ~155–160) follow `MASTERING-THE-INTERNET.md` and
should be re-checked with it. The distinctness baseline was measured with
`tools/distinct.py` over seventeen live sites on that date.

Search policy, checked 2026-07-30 — re-check before relying on it:

- [Google Search spam policies](https://developers.google.com/search/docs/essentials/spam-policies)
  — scaled content abuse and the doorway-page definition
- [Scaled content abuse background](https://www.breaklineagency.com/guide-to-googles-scaled-content-abuse/)
  — added March 2024, still governing in 2026
