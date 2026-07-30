#!/usr/bin/env python3
"""Hand a question to whatever model is in the chat, and take the answer
back safely.

These tools deliberately refuse to guess. `brief.py` won't pick an
archetype when two purposes compete; `threads.py` holds a fragment it
can't place; a facts contract stays full of marked blanks. Each refusal
is correct and each one leaves a question a human — or a model — has to
answer.

There is already a model in the room. So instead of calling an API, this
prints a **self-contained block you paste into any chat**, and reads the
reply back. No API key, no SDK, no vendor, no per-call cost, and nothing
here breaks when a provider changes a parameter name.

Three properties make it portable rather than Claude-specific:

  1. **The block carries its own rules.** A fresh chat knows nothing
     about this system, so every ask restates the constraints it must
     obey — never invent a fact, give a reason not a score, say
     "unknown" rather than guess. The rules travel with the question.
  2. **The reply parser assumes a chatty model.** Every assistant wraps
     JSON in "Here's the JSON you asked for:" and a code fence, and some
     add a summary afterwards. The parser digs the object out of prose,
     fences, and surrounding chatter, and takes the largest valid
     candidate. This is where "works in any chat" is actually won.
  3. **Model answers are labelled, never merged as verified.** Anything
     that comes back carries `via: model`, the date, and the ask id.
     A model-supplied fact is a *proposal*; it never silently becomes a
     fact the gate treats as checked.

And the rule inherited from the rest of the toolchain: **a model may
propose, raise a hold, or fill a blank. It may never drop anything.**

Usage:
    python3 tools/handoff.py primer
    python3 tools/handoff.py ask archetype --text "cabin, nightly, also for sale"
    python3 tools/handoff.py ask facts --text "..." --archetype service
    python3 tools/handoff.py ask link --text "frag A" --text "frag B"
    python3 tools/handoff.py apply --reply reply.txt
    python3 tools/handoff.py --selftest
"""

import argparse
import json
import re
import sys
from datetime import date

# The rules a fresh chat cannot know. Paste once at the top of a chat, or
# rely on each ask restating the subset it needs.
PRIMER = """\
You are helping run a build-and-capture system. Four rules govern every
answer you give it, and they override your usual defaults:

1. NEVER INVENT A FACT. If something is not stated in what you are given,
   the answer is "unknown". A plausible guess is worse than a blank here,
   because blanks are visible and guesses are not.
2. GIVE A REASON, NOT A SCORE. Every judgement must carry a sentence
   someone can disagree with. "0.78" cannot be argued with; "the price
   is the visitor's question, the bedroom count only describes it" can.
3. NEVER DISCARD ANYTHING. You may propose, flag, or say "needs a human".
   You may not recommend deleting, filing away, or ignoring any input.
4. WRITING STYLE IS NEVER EVIDENCE. Capitals, punctuation, terseness,
   fragments and stream-of-thought carry no signal about quality. Judge
   only what is stated.

Reply with a single JSON object matching the schema you are given. You
may write prose around it; the parser will find the object."""


ASKS = {
    "archetype": {
        "question": "Two site purposes both have evidence here. Which one "
                    "governs what the visitor arrives asking?",
        "context": "A site's archetype decides what counts as a blocking "
                   "failure at the gate, so a wrong pick is worse than no "
                   "pick. Choose only if one purpose clearly governs; if "
                   "the text describes two different sites, say so.",
        "schema": {
            "type": "object",
            "properties": {
                "archetype": {"type": "string", "enum": [
                    "service", "lodging", "venue", "listing", "index",
                    "info", "two-sites", "unknown"]},
                "reason": {"type": "string"},
                "governing_phrase": {"type": "string"},
            },
            "required": ["archetype", "reason"],
        },
        "rules": [1, 2],
    },
    "facts": {
        "question": "Which of these required facts are actually stated in "
                    "the text?",
        "context": "Return only facts the text states. Anything not "
                   "stated must come back as null — the blank is then "
                   "kept visible and the build is correctly blocked.",
        "schema": {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "object",
                    "description": "fact name -> stated value, or null",
                },
                "notes": {"type": "string"},
            },
            "required": ["facts"],
        },
        "rules": [1, 3],
    },
    "link": {
        "question": "Do these fragments belong to the same idea?",
        "context": "They share no repeated words, which is why a literal "
                   "match missed them. Fragments arrive random and "
                   "resolve later, so an early fragment may look "
                   "unrelated until a later one explains it. Say "
                   "'unrelated' only if you are confident.",
        "schema": {
            "type": "object",
            "properties": {
                "same_idea": {"type": "string",
                              "enum": ["yes", "no", "unclear"]},
                "reason": {"type": "string"},
                "shared_subject": {"type": "string"},
            },
            "required": ["same_idea", "reason"],
        },
        "rules": [2, 3, 4],
    },
}

RULE_TEXT = {
    1: "NEVER INVENT A FACT — anything not stated is \"unknown\" or null.",
    2: "GIVE A REASON, NOT A SCORE — one sentence someone can disagree with.",
    3: "NEVER DISCARD ANYTHING — you may flag or defer, never delete.",
    4: "WRITING STYLE IS NEVER EVIDENCE — caps, terseness and fragments "
       "carry no signal.",
}


def ask_id(kind, payload):
    """Short stable id so a reply can be matched to its question."""
    import hashlib
    blob = kind + "|" + "|".join(payload)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8]


def render_ask(kind, texts, extra=None):
    spec = ASKS[kind]
    aid = ask_id(kind, texts)
    out = []
    add = out.append

    add("─" * 64)
    add("PASTE EVERYTHING BELOW THIS LINE INTO ANY MODEL'S CHAT")
    add("─" * 64)
    add("")
    add("## Question")
    add(spec["question"])
    add("")
    add("## Context")
    add(spec["context"])
    if extra:
        add("")
        for k, v in extra.items():
            add("%s: %s" % (k, v))
    add("")
    add("## Input")
    for i, t in enumerate(texts, 1):
        label = "Fragment %d" % i if len(texts) > 1 else "Text"
        add("%s:" % label)
        for line in t.strip().split("\n"):
            add("  " + line.strip())
    add("")
    add("## Rules that override your defaults")
    for n in spec["rules"]:
        add("- %s" % RULE_TEXT[n])
    add("")
    add("## Reply with one JSON object matching this schema")
    add("```json")
    add(json.dumps(spec["schema"], indent=2))
    add("```")
    add("")
    add("Include this line verbatim inside the object so the reply can be")
    add("matched to its question:")
    add('  "ask_id": "%s"' % aid)
    add("")
    add("Prose around the JSON is fine.")
    add("─" * 64)
    return "\n".join(out), aid


# --- reading the reply back ------------------------------------------

FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def extract_json(reply):
    """Dig a JSON object out of whatever a chat model wrapped it in.

    Handles fenced blocks, bare objects, preamble and trailing summary.
    Returns the largest valid object found, or None."""
    candidates = []

    for m in FENCE.finditer(reply):
        candidates.append(m.group(1))

    # Bare objects: scan for balanced braces, ignoring braces in strings.
    depth, start, in_str, esc = 0, None, False, False
    for i, ch in enumerate(reply):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
                if depth == 0 and start is not None:
                    candidates.append(reply[start:i + 1])

    best = None
    for c in candidates:
        try:
            obj = json.loads(c)
        except ValueError:
            continue
        if isinstance(obj, dict) and (best is None or len(c) > best[0]):
            best = (len(c), obj)
    return best[1] if best else None


def stamp(obj, aid=None):
    """Mark provenance. A model answer is a proposal, never a fact."""
    obj = dict(obj)
    obj["via"] = "model"
    obj["received"] = date.today().isoformat()
    if aid:
        obj.setdefault("ask_id", aid)
    obj["status"] = "proposed — not verified"
    return obj


def validate(kind, obj):
    """Minimal shape check. Missing required keys is a rejection, not a
    silent default — a half-answer applied quietly is worse than none."""
    spec = ASKS.get(kind)
    if not spec:
        return ["unknown ask kind %r" % kind]
    problems = []
    for key in spec["schema"].get("required", []):
        if key not in obj:
            problems.append("missing required key %r" % key)
    props = spec["schema"].get("properties", {})
    for key, val in obj.items():
        allowed = props.get(key, {}).get("enum")
        if allowed and val not in allowed:
            problems.append("%r is not one of %s" % (val, allowed))
    return problems


def infer_kind(obj):
    """Work out which ask a reply answers, from its keys."""
    for kind, spec in ASKS.items():
        req = set(spec["schema"].get("required", []))
        if req and req <= set(obj):
            return kind
    return None


# ---------------------------------------------------------------------

MESSY_REPLIES = [
    # The common case: preamble, fence, trailing summary.
    ('Sure! Here\'s the JSON you asked for:\n\n```json\n'
     '{"archetype": "listing", "reason": "the price is the visitor\'s '
     'question", "ask_id": "abc12345"}\n```\n\nLet me know if you\'d '
     'like me to adjust anything.', "archetype", "listing"),
    # Bare object, no fence.
    ('{"same_idea": "yes", "reason": "both describe the permit sweep"}',
     "link", "yes"),
    # Two objects — the schema echo first, then the answer. Largest wins.
    ('You gave me this schema: {"type": "object"}\n\nMy answer:\n'
     '{"archetype": "service", "reason": "reachability is the question '
     'being asked here", "governing_phrase": "service radius"}',
     "archetype", "service"),
    # Fence without a language tag, braces inside a string value.
    ('```\n{"same_idea": "no", "reason": "one is about {cabins}, the '
     'other about invoicing"}\n```', "link", "no"),
]


def selftest():
    failed = []

    def check(label, cond):
        print("%s %s" % ("ok  " if cond else "FAIL", label))
        if not cond:
            failed.append(label)

    for i, (reply, kind, want) in enumerate(MESSY_REPLIES, 1):
        obj = extract_json(reply)
        got = obj.get("archetype") or obj.get("same_idea") if obj else None
        check("messy reply %d parsed (%s)" % (i, want), got == want)
        check("  kind inferred as %s" % kind, infer_kind(obj or {}) == kind)

    # A reply with no JSON at all must fail loudly, not silently.
    check("prose-only reply returns None",
          extract_json("I think it's probably a listing, honestly.") is None)

    # A half-answer is rejected rather than defaulted.
    check("missing required key is rejected",
          validate("archetype", {"archetype": "listing"}) != [])
    check("bad enum value is rejected",
          validate("archetype", {"archetype": "shop", "reason": "x"}) != [])
    check("complete answer validates",
          validate("archetype", {"archetype": "listing", "reason": "x"}) == [])

    # Provenance is never optional.
    s = stamp({"archetype": "listing", "reason": "x"}, "abc12345")
    check("answer is stamped as model-supplied and unverified",
          s["via"] == "model" and "not verified" in s["status"]
          and s["received"] == date.today().isoformat())

    # The ask must carry its own rules, or a fresh chat can't obey them.
    body, aid = render_ask("facts", ["licensed plumber"],
                           {"Archetype": "service"})
    check("ask restates the never-invent rule", "NEVER INVENT A FACT" in body)
    check("ask embeds a matchable id", aid in body and len(aid) == 8)
    check("ask is stable for the same input",
          render_ask("facts", ["licensed plumber"])[1] == aid)

    total = len(MESSY_REPLIES) * 2 + 8
    print("\n%d/%d passed" % (total - len(failed), total))
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("primer", help="rules block to paste at the top of a chat")

    p = sub.add_parser("ask", help="emit a question for the model in the chat")
    p.add_argument("kind", choices=sorted(ASKS))
    p.add_argument("--text", action="append", default=[], required=False)
    p.add_argument("--archetype", help="context for a facts ask")

    p = sub.add_parser("apply", help="read a model's reply back in")
    p.add_argument("--reply", help="file with the reply; omit to read stdin")
    p.add_argument("--kind", choices=sorted(ASKS))
    p.add_argument("--json", action="store_true")

    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    if args.cmd == "primer":
        print(PRIMER)
        return

    if args.cmd == "ask":
        if not args.text:
            ap.error("give at least one --text")
        extra = {"Archetype": args.archetype} if args.archetype else None
        body, _ = render_ask(args.kind, args.text, extra)
        print(body)
        return

    if args.cmd == "apply":
        raw = (open(args.reply, encoding="utf-8").read() if args.reply
               else sys.stdin.read())
        obj = extract_json(raw)
        if obj is None:
            sys.exit("error: no JSON object found in the reply. The model "
                     "may have answered in prose — ask it again for the "
                     "object, or paste just that part.")
        kind = args.kind or infer_kind(obj)
        if not kind:
            sys.exit("error: can't tell which question this answers. "
                     "Re-run with --kind.")
        problems = validate(kind, obj)
        if problems:
            sys.exit("error: reply doesn't match the %s schema:\n  %s"
                     % (kind, "\n  ".join(problems)))
        result = stamp(obj)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("%s answer accepted, marked %s" % (kind, result["status"]))
            for k, v in result.items():
                if k not in ("via", "received", "status"):
                    print("  %-18s %s" % (k, v))
            print("\nRecorded as a proposal. It is not a verified fact and")
            print("the gate will still treat the blank as blank until a")
            print("human confirms it.")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
