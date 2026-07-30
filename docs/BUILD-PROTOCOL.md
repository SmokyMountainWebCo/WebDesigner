# Build protocol — the order of operations for every site

> **Owns:** the sequence run before, during and after every build — how
> the field is determined, what facts must exist before code is written,
> and the gate a build has to clear before it deploys.
> **Not here:** how to make it look good (`DESIGN.md`,
> `DESIGN-LOOPHOLES.md`). How to make it fast (`INTERNET-SCIENCE.md`).
> How to get it found (`MASTERING-THE-INTERNET.md`).

Five phases. Each ends in something checkable, and **phase 4 is
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

Then three rules that only bite at scale:

- **A shared asset is served once.** At one site, embedding fonts buys a
  zero-request page. At forty cross-linked sites it's the same megabytes
  forty times — see `library/patterns/embedded-fonts-break-even.md`.
- **Every site gets a distinct link-preview card**, generated from the
  same template with its own data
  (`library/patterns/link-preview-card.md`). Forty sites sharing one
  card is forty identical grey boxes in a feed.
- **Templated sameness is visible from the outside.** Forty pages with the
  same headline shape and one swapped noun reads as spam to a person and
  to a search engine. The dialect layer has to carry real per-site
  difference — different questions answered, different proof, different
  photographs — or the set is worth less than any one site in it.

---

## Sources and date

Written **2026-07-30**. The checks encode failures observed in a real
twelve-page corpus and a twenty-site deployment; the thresholds
(title ~60, description ~155–160) follow `MASTERING-THE-INTERNET.md` and
should be re-checked with it.
