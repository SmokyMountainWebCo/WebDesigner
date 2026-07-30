#!/usr/bin/env python3
"""Turn a description of a build into a brief the gate can act on:
archetype, facts contract, and the exact preflight command.

This is the missing joint. A capture system can tell you an idea came
together; `build.py` and `preflight.py` can turn a finished folder into a
deployable site. Nothing connected the two, so every build began by
re-deriving Phase 0 and Phase 1 of `docs/BUILD-PROTOCOL.md` from memory —
which is exactly how a site ends up finished-looking and undeployable,
holding nineteen blanks nobody listed at the start.

What it will not do, and these are the point:

  * **It never invents a fact.** Every item in the contract it cannot
    find stays a marked blank in `⟨angle brackets⟩` — the form
    `preflight.py` greps for. A brief full of visible blanks is the
    correct output; a brief with plausible guesses is the failure this
    whole protocol exists to prevent.
  * **It refuses rather than guesses the archetype.** The archetype is an
    argument to the gate that decides what counts as a blocking failure,
    so getting it wrong is worse than not having it. When two archetypes
    both have evidence, it reports both and picks neither.
  * **It gives reasons, not scores.** Every determination names the
    phrase that decided it, so you can disagree with it.

Usage:
    python3 tools/brief.py "cabin rental, sleeps 8, needs booking"
    echo "..." | python3 tools/brief.py --stdin
    python3 tools/brief.py "..." --known phone=8655551234 --known hours="9-5"
    python3 tools/brief.py --selftest
"""

import argparse
import json
import re
import sys

# Phase 0 of docs/BUILD-PROTOCOL.md. Evidence comes in two kinds, and
# keeping them apart is what stops a subject word from choosing the
# archetype:
#
#   form  — declares what the site is *for*. "directory of", "for sale",
#           "book", "service radius". This is the visitor's question.
#   topic — names what it is *about*. "cabin", "plumber", "brewery".
#
# A directory of cabin cleaners is an index, not lodging; "cabin" is its
# subject, not its purpose. So form outranks topic, and only a clash of
# two *forms* is a real ambiguity worth refusing on.
ARCHETYPES = {
    "service": {
        "asks": "Can you fix this, and can you come now?",
        "owes": "Reachability, proof of licence, service area",
        "schema": "Plumber, Electrician, LocalBusiness…",
        "next": "a click-to-call link",
        "form": r"\b(service (?:area|radius)|emergency call.?outs?|licen[cs]ed|"
                r"call.?outs?|free estimates?|same.day|24/7)\b",
        "topic": r"\b(plumb\w*|electric\w*|hvac|roof\w*|repair\w*|install\w*|"
                 r"contractor|handyman|septic|landscap\w*|pest control|"
                 r"locksmith|mobile mechanic)\b",
        "facts": ["legal business name", "phone", "licence number",
                  "insurance status", "service radius", "hours",
                  "emergency policy", "warranty terms"],
    },
    "lodging": {
        "asks": "What is it actually like there?",
        "owes": "Rooms, the space, dates",
        "schema": "LodgingBusiness, VacationRental",
        "next": "a booking or availability action",
        "form": r"\b(book(?:ing|able)?|nightly|per night|check.?in|"
                r"availability|minimum stay|airbnb|vrbo|short.term rental)\b",
        "topic": r"\b(cabin|chalet|lodge|sleeps?\s*\d+|bedroom|bunk|"
                 r"hot tub|guest)\b",
        "facts": ["address", "sleeps / bed / bath", "amenities",
                  "permit status", "cancellation policy",
                  "real photographs", "booking method"],
    },
    "venue": {
        "asks": "What's on, and what's it like in the room?",
        "owes": "Lineup, hours, the space",
        "schema": "EventVenue, Restaurant",
        "next": "tickets, menu or hours",
        "form": r"\b(menu|tickets?|reservations?|lineup|seating|"
                r"now serving|doors at)\b",
        "topic": r"\b(restaurant|cafe|café|brewery|taproom|bar\b|"
                 r"live music|event space|venue)\b",
        "facts": ["address", "hours", "capacity",
                  "lineup or menu source", "ticketing"],
    },
    "listing": {
        "asks": "What is this property and what does it cost?",
        "owes": "Facts, figures, photographs",
        "schema": "RealEstateListing",
        "next": "a way to enquire",
        "form": r"\b(for sale|asking price|listing price|mls|under contract|"
                r"appraisal|disclosur\w*)\b",
        "topic": r"\b(acre\w*|square (?:feet|foot|ft)|sq\.? ?ft|parcel|"
                 r"zoning|lot \d)\b",
        "facts": ["address", "price", "acreage / square footage",
                  "permit or zoning status", "disclosures", "photographs"],
    },
    "index": {
        "asks": "Who's in this, and can I trust the list?",
        "owes": "Coverage and its rules",
        "schema": "CollectionPage, ItemList",
        "next": "into a member's own site",
        "form": r"\b(directory|index of|registry|the list|members?|"
                r"round.?up|who's who|catalog\w*|every \w+ in|apply to join)\b",
        "topic": r"\b(coverage|inclusion criteria|entries)\b",
        # An index owes its rules, not a licence number.
        "facts": ["what qualifies for inclusion", "coverage boundary",
                  "how entries are verified", "correction process",
                  "update cadence"],
    },
    "info": {
        "asks": "What is this?",
        "owes": "A straight answer",
        "schema": "—",
        "next": "—",
        "form": None,               # the fallback, never matched directly
        "topic": None,
        "facts": ["what it is", "who it's for", "who published it"],
    },
}

BLANK = "⟨%s⟩"


def _matches(pattern, text):
    if not pattern:
        return []
    return sorted({m.group(0).lower()
                   for m in re.finditer(pattern, text, re.I)})


def determine(text):
    """Return (archetype|None, evidence, competing).

    Form evidence decides. Topic evidence only breaks a tie when no
    archetype declared a form, and a clash of two forms is refused."""
    form, topic = {}, {}
    for name, spec in ARCHETYPES.items():
        f = _matches(spec["form"], text)
        t = _matches(spec["topic"], text)
        if f:
            form[name] = f
        if t:
            topic[name] = t

    layer = form or topic
    if not layer:
        return "info", [], {}
    if len(layer) == 1:
        name = next(iter(layer))
        # Report the topic words too — they are why you'd disagree.
        return name, layer[name] + topic.get(name, []), {}

    # Two or more archetypes declared a purpose. The archetype decides
    # what the gate treats as a blocking failure, so a wrong pick is
    # worse than no pick. Report and refuse.
    return None, [], layer


def contract(archetype, known):
    """Facts contract with supplied values filled and the rest marked."""
    rows = []
    for fact in ARCHETYPES[archetype]["facts"]:
        key = re.sub(r"[^a-z0-9]+", "_", fact.lower()).strip("_")
        # Match on any supplied key that is a prefix of the fact's slug,
        # so --known phone=… fills "phone" without needing the full name.
        value = None
        for k, v in known.items():
            slug = re.sub(r"[^a-z0-9]+", "_", k.lower()).strip("_")
            if slug and (slug in key or key.startswith(slug)):
                value = v
                break
        rows.append((fact, value))
    return rows


def render(text, archetype, evidence, competing, known, sources, base, draft):
    out = []
    add = out.append

    add("BUILD BRIEF")
    add("=" * 60)
    add("")
    add("Description:")
    for line in text.strip().split("\n"):
        add("  " + line.strip())
    add("")

    if archetype is None:
        add("ARCHETYPE: NOT DETERMINED — refusing to guess")
        add("")
        add("  More than one archetype has real evidence here. The")
        add("  archetype is an argument to the gate: it decides what")
        add("  counts as a blocking failure, so a wrong pick is worse")
        add("  than no pick.")
        add("")
        for name, found in sorted(competing.items()):
            add("    %-9s evidence: %s" % (name, ", ".join(found[:5])))
        add("")
        add("  Re-run with --archetype <name> once you've decided, or")
        add("  split this into two builds if it is genuinely two sites.")
        return "\n".join(out), 2

    spec = ARCHETYPES[archetype]
    add("ARCHETYPE: %s" % archetype)
    if evidence:
        add("  decided by: %s" % ", ".join(evidence[:6]))
    else:
        add("  decided by: nothing matched another archetype — the fallback")
    add("")
    add("  visitor arrives asking:  %s" % spec["asks"])
    add("  the page owes them:      %s" % spec["owes"])
    add("  schema type:             %s" % spec["schema"])
    add("  the next step:           %s" % spec["next"])
    add("")

    rows = contract(archetype, known)
    have = sum(1 for _, v in rows if v)
    add("FACTS CONTRACT — %d of %d in hand" % (have, len(rows)))
    add("  Do not start until these are known. A blank is never filled")
    add("  with a plausible guess.")
    add("")
    for fact, value in rows:
        if value:
            add("  [x] %-28s %s" % (fact, value))
        else:
            add("  [ ] %-28s %s" % (fact, BLANK % fact))
    add("")

    if sources:
        add("SOURCES — %d" % len(sources))
        for s in sources:
            add("  %s" % s)
        add("")

    missing = len(rows) - have
    add("GATE")
    target = base or "https://⟨the-real-host⟩/"
    flag = " --draft" if (draft or missing) else ""
    add("  python3 tools/preflight.py site/ \\")
    add("      --archetype %s --base %s%s" % (archetype, target, flag))
    add("")
    if missing:
        add("  %d fact%s still blank, so this build cannot launch. The"
            % (missing, "" if missing == 1 else "s"))
        add("  --draft flag says so out loud rather than letting a")
        add("  finished-looking site sit undeployable.")
    else:
        add("  Contract complete. Drop --draft when the build is real.")

    return "\n".join(out), (1 if missing else 0)


# Exit 1 is the *correct* result for a brief with unfilled facts — it is
# the tool saying "this cannot launch yet." Exit 2 is a refusal to pick an
# archetype. Only a complete contract exits 0.
SELFTEST = [
    ("cabin rental in the smokies, sleeps 8, hot tub, booking button",
     "lodging", 1),
    ("licensed plumber, emergency call outs, service radius 30 miles",
     "service", 1),
    # "cabin" here is the subject, not the purpose. Form must win, or
    # every directory about lodging gets built as lodging.
    ("a directory of every cabin cleaner in the county, members apply",
     "index", 1),
    ("5 acres for sale, asking price 240k, zoning is R-1", "listing", 1),
    ("brewery with live music and a menu, reservations on weekends",
     "venue", 1),
    ("a page explaining what the co-op is", "info", 1),
    # A property listing that happens to be a cabin is still a listing —
    # one declared purpose, so no refusal.
    ("cabin sleeps 6, for sale, asking price 400k", "listing", 1),
    # Genuinely two purposes: somewhere to book *and* a service sold to
    # other owners. Two sites, or a decision. Never a coin flip.
    ("book our cabin nightly, and we also do licensed cleaning for "
     "other owners, service radius 20 miles", None, 2),
    # A complete contract is the only way to exit 0.
    ("a page explaining what the co-op is", "info", 0,
     {"what it is": "a co-op", "who": "members", "who published": "us"}),
]


def selftest():
    failed = 0
    for case in SELFTEST:
        text, want, want_code = case[0], case[1], case[2]
        known = case[3] if len(case) > 3 else {}
        arch, ev, comp = determine(text)
        _, code = render(text, arch, ev, comp, known, [], None, False)
        ok = arch == want and code == want_code
        failed += not ok
        print("%s %-9s %s" % ("ok  " if ok else "FAIL",
                             arch if arch else "REFUSED", text[:52]))
        if not ok:
            print("      wanted %s / exit %s, got %s / exit %s"
                  % (want, want_code, arch, code))

    # A supplied fact must fill its row and nothing else.
    rows = contract("service", {"phone": "865-555-0100"})
    filled = [f for f, v in rows if v]
    ok = filled == ["phone"]
    failed += not ok
    print("%s known fact fills exactly one row (%s)"
          % ("ok  " if ok else "FAIL", ", ".join(filled) or "none"))

    # Blanks must be greppable by preflight.
    text, _ = render("licensed plumber", "service", [], {}, {}, [], None, False)
    ok = "⟨licence number⟩" in text
    failed += not ok
    print("%s blanks are marked in the form the gate greps for"
          % ("ok  " if ok else "FAIL"))

    total = len(SELFTEST) + 2
    print("\n%d/%d passed" % (total - failed, total))
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="what the build is")
    ap.add_argument("--stdin", action="store_true", help="read the text from stdin")
    ap.add_argument("--archetype", choices=sorted(ARCHETYPES),
                    help="decide it yourself instead of inferring")
    ap.add_argument("--known", action="append", default=[], metavar="KEY=VALUE",
                    help="a fact already in hand; repeatable")
    ap.add_argument("--source", action="append", default=[],
                    help="where this came from; repeatable")
    ap.add_argument("--base", help="the real host, for the gate command")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    text = sys.stdin.read() if args.stdin else (args.text or "")
    if not text.strip():
        ap.error("give a description, or --stdin")

    known = {}
    for pair in args.known:
        if "=" not in pair:
            sys.exit("error: --known wants KEY=VALUE, got %r" % pair)
        k, v = pair.split("=", 1)
        known[k.strip()] = v.strip()

    if args.archetype:
        archetype, evidence, competing = args.archetype, ["supplied"], {}
    else:
        archetype, evidence, competing = determine(text)

    if args.json:
        rows = contract(archetype, known) if archetype else []
        print(json.dumps({
            "archetype": archetype,
            "decided_by": evidence,
            "competing": competing,
            "facts": [{"fact": f, "value": v, "blank": v is None}
                      for f, v in rows],
            "sources": args.source,
        }, ensure_ascii=False, indent=2))
        sys.exit(0 if archetype and all(v for _, v in rows) else
                 (2 if archetype is None else 1))

    body, code = render(text, archetype, evidence, competing, known,
                        args.source, args.base, args.draft)
    print(body)
    sys.exit(code)


if __name__ == "__main__":
    main()
