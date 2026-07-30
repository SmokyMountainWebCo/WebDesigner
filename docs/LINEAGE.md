# Lineage — where these rules came from

> **Owns:** the intellectual ancestry of this repo's house rules. Which
> book or which decision each rule descends from, so the rules can be
> argued with rather than merely obeyed.
> **Not here:** the rules themselves (`README.md`, `CLAUDE.md`). How to
> apply them (`BUILD-PROTOCOL.md`, `DESIGN.md`).

Every house rule in this repo is somebody's hard-won conclusion, usually
reached decades ago at some cost. A rule with a source can be
re-examined when conditions change. A rule without one becomes ritual,
and gets followed after it stops being true.

**A note on how to read this.** These are the books' central arguments,
stated as accurately as I can and sourced below — not a substitute for
reading them. Any specific claim you plan to lean on should be checked
against the book itself.

---

## The network was built to survive, which is why anything degrades at all

**Where Wizards Stay Up Late: The Origins of the Internet** — Katie
Hafner and Matthew Lyon, 1996.

Packet switching was arrived at independently by Paul Baran at RAND and
Donald Davies at the NPL, and the ARPANET was built on a principle that
now reads as obvious and wasn't: **put the intelligence at the endpoints
and keep the network dumb.** No central authority, no single node whose
loss stops the system, every packet finding its own way.

That decision is why the phrase "degrade visibly" is even coherent.
A network that assumed everything works would have no failure modes to
degrade *through* — it would simply stop. The web inherited a substrate
whose whole design premise is that pieces will be missing, and HTML
inherited the same temperament: an unknown tag is ignored rather than
fatal, a missing stylesheet leaves readable text.

**The rule it explains:** *Degrade visibly, never silently.* We didn't
invent that posture; we're building on a system that was designed by
people who assumed loss.

There's a founding anecdote worth keeping. The first message sent over
the ARPANET — UCLA to SRI, 29 October 1969 — was meant to be `LOGIN`.
The system crashed after two characters, so the first thing the internet
ever carried was **`LO`**. The network's opening moment was a partial
failure that still delivered something legible. That is progressive
enhancement as a temperament, thirty years before it had a name.

---

## Nothing here was invented by one person

**The Innovators: How a Group of Hackers, Geniuses, and Geeks Created the
Digital Revolution** — Walter Isaacson, 2014.

Isaacson's argument across the whole arc — Lovelace and Babbage, ENIAC,
the transistor, the microchip, the packet-switched network, the personal
computer, the web — is that **the lone-genius story is almost always
wrong.** The advances came from collaboration, from teams, and from
people combining work they did not personally originate.

**The rule it explains:** *Prefer the platform to a dependency.* The
platform is not a vendor's product; it is the accumulated, standardised
output of exactly that collaborative process. `:has()`, `<dialog>`,
container queries, `clamp()` and OKLCH each arrived because a lot of
people argued a proposal into a spec. Reaching for a library before
checking MDN is choosing one team's work over everybody's.

---

## Invention is the cheap half — the expensive half is getting it in front of anyone

**Dealers of Lightning: Xerox PARC and the Dawn of the Computer Age** —
Michael Hiltzik, 1999.

Xerox PARC, from 1970, produced the graphical user interface, the Alto,
Ethernet, the laser printer, WYSIWYG editing and Smalltalk. Xerox
commercialised almost none of it. Other companies shipped those ideas and
built the industry on them.

This is the least comfortable book on the list, because its lesson is not
about technique at all. **Building the thing is not the constraint.**
PARC was, by a wide margin, the best building operation of its era, and
being the best builder was not sufficient — not even close.

**The rule it explains:** the one this repo enforces in
`BUILD-PROTOCOL.md` phase 5 and phase 3 — *record what you built, declare
whether it is launching, and give every page a link preview.* Those look
like housekeeping. They are distribution. A finished build nobody can
find, share, or verify exists is the PARC failure at small scale, and the
failure mode is not that the work was bad.

---

## The web's own standards movement, written down

**Designing with Web Standards** — Jeffrey Zeldman (third edition with
Ethan Marcotte, 2009 — the ISBN `0321616952`).

This is the most direct ancestor of this repo. Zeldman's case, made when
the industry was still shipping browser-specific sites and table layouts,
was for **separating structure from presentation from behavior**, writing
**semantic markup**, building for **forward compatibility** rather than
for today's browsers, and layering enhancement over content that already
works — the argument that gave *progressive enhancement* its name and its
constituency.

**The rules it explains, nearly all of them:**

- *Content lives in the HTML; scripts hide and animate only after setting
  a class.*
- *Semantic elements. Accessibility is a requirement, not a section.*
- *Works without JavaScript, then better with it.*

Two things worth saying plainly. The book's specific advice has dated
where the platform moved on — its era's browser workarounds are gone, and
some of what it argued for is now simply how browsers behave, which is
the best possible outcome for an argument. But the **principle outlasted
the tactics**, which is exactly why it belongs here rather than in a
history section: the reason this repo's pages still work with scripting
off is an argument somebody won in the early 2000s.

---

## What the set has in common

Read together, the four make one point from four directions: **the web is
not a product that was designed, it is a settlement that was negotiated,
and its accidents are load-bearing.**

That is the actual justification for this repo's temperament. Preferring
the platform, degrading visibly, keeping content in the HTML and shipping
one file with no dependencies are not aesthetic preferences. They are
what you do on a substrate that was built by many hands to survive
partial failure — and every rule here should be re-checked against that
substrate when it changes, not defended because it is written down.

---

## Sources and date

Checked **2026-07-30**. Publication details and central arguments are as
described in the sources below; the books themselves are the authority.

- Hafner, Katie & Lyon, Matthew. *Where Wizards Stay Up Late: The Origins
  of the Internet.* Simon & Schuster, 1996.
- Isaacson, Walter. [*The Innovators.*](https://www.simonandschuster.com/books/The-Innovators/Walter-Isaacson/9781476708706)
  Simon & Schuster, 2014.
- Hiltzik, Michael. *Dealers of Lightning: Xerox PARC and the Dawn of the
  Computer Age.* HarperBusiness, 1999.
- Zeldman, Jeffrey with Marcotte, Ethan. [*Designing with Web Standards,*
  3rd ed.](https://www.amazon.com/Designing-Web-Standards-Jeffrey-Zeldman/dp/0321616952)
  New Riders, 2009.
