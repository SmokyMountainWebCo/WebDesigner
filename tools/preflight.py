#!/usr/bin/env python3
"""Refuse to ship a build that isn't finished.

  python3 tools/preflight.py site/ --archetype service --base https://example.com/
  python3 tools/preflight.py site/ --archetype lodging --base https://x.dev/ --net
  python3 tools/preflight.py site/ --draft          # spec build / pitch, not launching

Runs every gate over a built site and exits non-zero if any FAIL. Written
to be the last thing between a folder and a deploy, so it is safe to put
in front of a mass build: one command, one exit code.

Every check here exists because the failure it catches actually happened
to a real site — not because it appears on a best-practices list. The
rationale for each is in docs/BUILD-PROTOCOL.md.

Severity:
  FAIL  blocks the deploy. Exit code 1.
  WARN  ship-able, but somebody decided to. Exit 0 unless --strict.
  NOTE  informational, never blocks.

Stdlib only. --net adds live URL checks and is the only thing that
touches the network.
"""
import argparse, json, os, re, sys, urllib.request, urllib.error
from collections import Counter

# Anything still holding a slot where a fact belongs. The angle-bracket
# forms are a house convention; the rest are the usual suspects.
#
# Deliberately narrow, and case-sensitive for the bare-word tokens. An
# earlier version matched /your[ _]name/i and flagged a form's "Your name"
# label plus two lines of ordinary prose. A blocking gate that cries wolf
# gets switched off, so precision beats recall here: only match forms that
# cannot be normal English.
PLACEHOLDER = re.compile(
    r"⟨[^⟩]*⟩"                      # ⟨need⟩, ⟨confirm terms⟩
    r"|\{\{[^}]*\}\}"                # {{TOKEN}}
    r"|\[\[[^\]]*\]\]"               # [[TOKEN]]
    r"|\bYOUR_[A-Z]+\b"              # YOUR_NAME — a token, not a sentence
    r"|\bTBD\b|\bFIXME\b|\bTODO\b"   # uppercase only
    r"|\bLorem ipsum\b")

ARCHETYPES = {
    # what the visitor arrives asking -> what the page owes them
    "service":  dict(schema={"LocalBusiness", "Plumber", "Electrician", "HVACBusiness",
                             "GeneralContractor", "HomeAndConstructionBusiness", "ProfessionalService",
                             "Locksmith", "RoofingContractor", "MovingCompany", "HousePainter"},
                     needs=["telephone", "areaServed"],
                     cta=r"tel:", cta_name="a click-to-call link"),
    "lodging":  dict(schema={"LodgingBusiness", "VacationRental", "Hotel", "BedAndBreakfast", "Resort"},
                     needs=["address"],
                     cta=r"book|reserve|check\s*(?:dates|availability)|inquire",
                     cta_name="a booking or availability action"),
    "venue":    dict(schema={"EventVenue", "PerformingArtsTheater", "Restaurant", "FoodEstablishment",
                             "NightClub", "ComedyClub"},
                     needs=["address"],
                     cta=r"tickets?|reserve|menu|hours|book",
                     cta_name="tickets, menu or hours"),
    "listing":  dict(schema={"RealEstateListing", "SingleFamilyResidence", "Residence", "Product", "Offer"},
                     needs=[],
                     cta=r"tel:|mailto:|inquire|schedule|tour",
                     cta_name="a way to enquire"),
    "index":    dict(schema={"CollectionPage", "ItemList", "WebSite", "DataCatalog"},
                     needs=[],
                     cta=None, cta_name=None),
    "info":     dict(schema=set(), needs=[], cta=None, cta_name=None),
}

RE_ATTR = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
RE_META = re.compile(r"<meta\s+([^>]+?)/?>", re.I)
RE_STYLE = re.compile(r"<style[^>]*>(.*?)</style>", re.I | re.S)
RE_SCRIPT_ANY = re.compile(r"<script[^>]*>.*?</script>", re.I | re.S)
RE_JSONLD = re.compile(r"<script[^>]+ld\+json[^>]*>(.*?)</script>", re.I | re.S)
RE_FF_DATA = re.compile(r"url\(data:[^;]*;base64,([A-Za-z0-9+/=]+)\)")


def attrs(s):
    return {m.group(1).lower(): (m.group(2) or m.group(3) or m.group(4) or "")
            for m in RE_ATTR.finditer(s)}


def visible_text(html):
    """Body text with script/style/head stripped — what a human actually reads."""
    b = html[html.find("<body"):] if "<body" in html else html
    b = RE_SCRIPT_ANY.sub(" ", b)
    b = RE_STYLE.sub(" ", b)
    b = re.sub(r"<!--.*?-->", " ", b, flags=re.S)
    b = re.sub(r"<[^>]+>", " ", b)
    return re.sub(r"\s+", " ", b)


class Report:
    def __init__(self):
        self.rows = []

    def add(self, sev, page, check, msg):
        self.rows.append((sev, page, check, msg))

    def fail(self, *a): self.add("FAIL", *a)
    def warn(self, *a): self.add("WARN", *a)
    def note(self, *a): self.add("NOTE", *a)

    @property
    def fails(self): return [r for r in self.rows if r[0] == "FAIL"]
    @property
    def warns(self): return [r for r in self.rows if r[0] == "WARN"]


def head_meta(html):
    head = html[:html.find("</head>")] if "</head>" in html else html
    out = {}
    for m in RE_META.finditer(head):
        a = attrs(m.group(1))
        k = (a.get("property") or a.get("name") or "").lower()
        if k:
            out[k] = a.get("content", "")
    return head, out


def check_page(path, html, rep, args, page):
    head, metas = head_meta(html)
    text = visible_text(html)
    noindex = "noindex" in metas.get("robots", "").lower()

    # ── 1. unfinished content ────────────────────────────────────────────
    # The one that shipped: 19 placeholders sitting in a site called ready.
    ph = PLACEHOLDER.findall(text)
    if ph:
        c = Counter(ph)
        top = ", ".join("%s x%d" % (k.strip(), v) for k, v in c.most_common(4))
        sev = rep.warn if (args.draft or noindex) else rep.fail
        sev(page, "placeholders",
            "%d unfilled placeholder(s) in visible text: %s" % (len(ph), top))

    # A draft banner in the body while the page is indexable means the
    # draft guard was removed and the banner wasn't.
    if re.search(r"\bthis (?:page|site) is a (?:working )?draft\b|\bdraft\.\b", text[:4000], re.I):
        if not noindex and not args.draft:
            rep.fail(page, "draft-banner",
                     "visible draft language in the body but the page is indexable")
        else:
            rep.note(page, "draft-banner", "draft language present (page is noindex)")

    # ── 2. can it be found, and does it look right when shared ───────────
    if args.draft or noindex:
        rep.note(page, "indexable", "noindex — not launching")
    else:
        if not re.search(r'rel=["\']canonical', head, re.I):
            rep.warn(page, "canonical", "no rel=canonical")
    for need in ("og:title", "og:description", "og:image", "og:url"):
        if need not in metas:
            rep.fail(page, "link-preview", "missing %s — shares render as a bare box" % need)
    if "twitter:card" not in metas:
        rep.warn(page, "link-preview", "no twitter:card")
    if metas.get("og:image") and not metas.get("og:image:alt"):
        rep.warn(page, "link-preview", "og:image has no og:image:alt")

    # og:image must be an absolute URL and the file must exist
    img = metas.get("og:image", "")
    if img:
        if not re.match(r"^https?://", img):
            rep.fail(page, "og-image", "og:image is not absolute (%s) — crawlers won't resolve it" % img[:60])
        elif args.base:
            base = args.base.rstrip("/")
            if img.startswith(base):
                rel = img[len(base):].lstrip("/")
                local = os.path.join(args.root, rel)
                if not os.path.exists(local):
                    rep.fail(page, "og-image", "og:image points at %s which is not in the build" % rel)

    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    if not title or not title.group(1).strip():
        rep.fail(page, "title", "no <title>")
    else:
        n = len(" ".join(title.group(1).split()))
        if n > 62:
            rep.warn(page, "title", "%d chars — truncates in results around 60" % n)
    d = metas.get("description", "")
    if not d and not (args.draft or noindex):
        rep.warn(page, "description", "no meta description")
    elif len(d) > 165:
        rep.warn(page, "description", "%d chars — truncates around 155-160" % len(d))

    # ── 3. self-reference must point somewhere real ──────────────────────
    # The one that shipped: canonical, og:url and og:image all naming a
    # host that returned 404, so every preview came back empty.
    if args.base:
        base_host = re.sub(r"^https?://", "", args.base).rstrip("/").split("/")[0]
        for key in ("og:url", "og:image"):
            v = metas.get(key, "")
            if v.startswith("http"):
                h = re.sub(r"^https?://", "", v).split("/")[0]
                if h != base_host:
                    rep.fail(page, "host-drift",
                             "%s points at %s but the site deploys to %s" % (key, h, base_host))
        cm = re.search(r'rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', head, re.I)
        if cm:
            h = re.sub(r"^https?://", "", cm.group(1)).split("/")[0]
            if h != base_host:
                rep.fail(page, "host-drift",
                         "canonical points at %s but the site deploys to %s" % (h, base_host))

    # ── 4. structured data ───────────────────────────────────────────────
    types = []
    for blob in RE_JSONLD.findall(html):
        try:
            data = json.loads(blob)
        except (ValueError, json.JSONDecodeError) as e:
            rep.fail(page, "json-ld", "invalid JSON-LD: %s" % str(e)[:70])
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict):
                for n2 in (node.get("@graph") or [node]):
                    if isinstance(n2, dict) and "@type" in n2:
                        t = n2["@type"]
                        types += t if isinstance(t, list) else [t]
    arche = ARCHETYPES.get(args.archetype, ARCHETYPES["info"])
    if arche["schema"]:
        if not types:
            rep.fail(page, "json-ld", "no JSON-LD; %s pages need one of: %s"
                     % (args.archetype, ", ".join(sorted(arche["schema"])[:4])))
        elif not (set(types) & arche["schema"]):
            rep.warn(page, "json-ld", "@type %s isn't one the %s archetype expects"
                     % (types, args.archetype))
    blob_all = " ".join(RE_JSONLD.findall(html))
    for need in arche["needs"]:
        if types and ('"%s"' % need) not in blob_all:
            rep.warn(page, "json-ld", "%s archetype usually declares %s" % (args.archetype, need))

    # ── 5. the visitor's next step must exist ────────────────────────────
    if arche["cta"] and not (args.draft or noindex):
        if not re.search(arche["cta"], html, re.I):
            rep.fail(page, "call-to-action",
                     "no %s found — the page answers the question and then stops" % arche["cta_name"])

    # ── 6. accessibility ─────────────────────────────────────────────────
    if not re.search(r"<html[^>]*\blang=", html, re.I):
        rep.fail(page, "a11y", "<html> has no lang")
    vp = metas.get("viewport", "")
    if re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?![\d.])", vp):
        rep.fail(page, "a11y", "viewport disables zoom")
    if not vp:
        rep.fail(page, "a11y", "no viewport meta")

    h1s = re.findall(r"<h1\b", html, re.I)
    if len(h1s) == 0:
        rep.fail(page, "a11y", "no <h1>")
    elif len(h1s) > 1:
        rep.warn(page, "a11y", "%d <h1> elements" % len(h1s))
    levels = [int(l) for l in re.findall(r"<h([1-6])\b", html, re.I)]
    skips = sum(1 for a, b in zip(levels, levels[1:]) if b - a > 1)
    if skips:
        rep.warn(page, "a11y", "%d heading level skip(s)" % skips)

    imgs = [attrs(a) for a in re.findall(r"<img\b([^>]*)>", html, re.I | re.S)]
    noalt = [a for a in imgs if "alt" not in a]
    if noalt:
        rep.fail(page, "a11y", "%d <img> without alt" % len(noalt))
    nodim = [a for a in imgs if not ("width" in a and "height" in a)]
    if nodim:
        rep.warn(page, "cls", "%d <img> without width/height — layout shift" % len(nodim))

    ths = re.findall(r"<th\b([^>]*)>", html, re.I)
    noscope = [t for t in ths if "scope=" not in t.lower()]
    if noscope:
        rep.warn(page, "a11y", "%d <th> without scope" % len(noscope))

    css = " ".join(RE_STYLE.findall(html))
    if re.search(r"outline\s*:\s*(?:none|0)\b", css) and "focus-visible" not in css:
        rep.fail(page, "a11y", "outline:none with no :focus-visible rule — keyboard focus is invisible")

    # ── 7. weight ────────────────────────────────────────────────────────
    kb = len(html.encode()) / 1000
    if kb > args.budget:
        rep.warn(page, "weight", "%.0f KB exceeds the %d KB budget" % (kb, args.budget))
    return {"page": page, "kb": kb, "noindex": noindex, "metas": metas}


def check_site(pages, rep, args):
    """Checks that only make sense across the whole build."""
    # Font payload duplicated across pages. The one that shipped: 2.9 MB of
    # identical faces repeated across a cross-linked set.
    seen, dup = {}, 0
    for p in pages:
        for b64 in set(RE_FF_DATA.findall(p["html"])):
            n = len(b64) * 3 // 4
            if b64 in seen:
                dup += n
            else:
                seen[b64] = n
    if dup > 400_000 and len(pages) > 1:
        rep.warn("(site)", "fonts",
                 "%.1f MB of identical embedded fonts duplicated across %d pages — "
                 "share one cached stylesheet" % (dup / 1e6, len(pages)))

    # Internal links that go nowhere.
    names = {os.path.splitext(p["page"])[0] for p in pages} | {"index"}
    files = set(os.listdir(args.root))
    for p in pages:
        for href in re.findall(r'<a\b[^>]*href=["\']([^"\'#?]+)', p["html"]):
            if href.startswith(("http", "//", "mailto:", "tel:", "sms:", "#", "data:")):
                continue
            t = href.strip("/").split("/")[-1] or "index"
            if t not in names and href.lstrip("/") not in files:
                rep.fail(p["page"], "dead-link", "internal link goes nowhere: %s" % href)

    # A launching site should be reachable.
    if not args.draft:
        if not any(f in files for f in ("robots.txt",)):
            rep.note("(site)", "robots", "no robots.txt")
        elif os.path.exists(os.path.join(args.root, "robots.txt")):
            r = open(os.path.join(args.root, "robots.txt"), encoding="utf-8", errors="replace").read()
            if re.search(r"^\s*Disallow:\s*/\s*$", r, re.M):
                rep.fail("(site)", "robots", "robots.txt disallows everything but this is not a draft")


def check_net(pages, rep, args):
    urls = set()
    for p in pages:
        for k in ("og:image", "og:url"):
            v = p["metas"].get(k, "")
            if v.startswith("http"):
                urls.add(v)
    for u in sorted(urls):
        try:
            req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "preflight/1.0"})
            code = urllib.request.urlopen(req, timeout=20).status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            rep.fail("(net)", "url", "%s -> %s" % (u, type(e).__name__))
            continue
        if code >= 400:
            rep.fail("(net)", "url", "%s -> HTTP %d" % (u, code))
        else:
            rep.note("(net)", "url", "%s -> %d" % (u, code))


def main():
    ap = argparse.ArgumentParser(description="Gate a built site before deploy.")
    ap.add_argument("root", help="folder of built HTML")
    ap.add_argument("--archetype", default="info", choices=sorted(ARCHETYPES),
                    help="what job this site does (default: info)")
    ap.add_argument("--base", help="the URL this site actually deploys to")
    ap.add_argument("--draft", action="store_true",
                    help="spec build / pitch: placeholders and noindex are expected")
    ap.add_argument("--net", action="store_true", help="also check that og: URLs resolve")
    ap.add_argument("--budget", type=int, default=500, help="per-page KB budget (default 500)")
    ap.add_argument("--strict", action="store_true", help="treat WARN as blocking")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        sys.exit("error: %s is not a folder" % args.root)

    rep = Report()
    pages = []
    for fn in sorted(os.listdir(args.root)):
        if not fn.endswith((".html", ".htm")):
            continue
        html = open(os.path.join(args.root, fn), encoding="utf-8", errors="replace").read()
        info = check_page(os.path.join(args.root, fn), html, rep, args, fn)
        info["html"] = html
        pages.append(info)

    if not pages:
        sys.exit("error: no HTML found in %s" % args.root)

    check_site(pages, rep, args)
    if args.net:
        check_net(pages, rep, args)

    order = {"FAIL": 0, "WARN": 1, "NOTE": 2}
    rep.rows.sort(key=lambda r: (order[r[0]], r[1], r[2]))
    width = max(len(r[1]) for r in rep.rows) if rep.rows else 10
    for sev, page, check, msg in rep.rows:
        if sev == "NOTE" and not args.strict:
            continue
        print("  %-4s %-*s %-14s %s" % (sev, width, page, check, msg))

    n_f, n_w = len(rep.fails), len(rep.warns)
    print("\n  %d page(s) · %d FAIL · %d WARN · archetype=%s%s"
          % (len(pages), n_f, n_w, args.archetype, " · draft" if args.draft else ""))
    if n_f:
        # Telling somebody to pass --draft when they already did is the kind
        # of advice that teaches people to stop reading the output.
        print("  BLOCKED — fix the FAILs%s." %
              ("" if args.draft else " or mark the build --draft"))
        sys.exit(1)
    if n_w and args.strict:
        print("  BLOCKED — --strict treats warnings as blocking.")
        sys.exit(1)
    print("  PASS — clear to deploy.")


if __name__ == "__main__":
    main()
