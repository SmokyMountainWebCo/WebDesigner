#!/usr/bin/env python3
"""Measure how alike a set of sites really is.

  python3 tools/distinct.py sites/            # a folder of folders, or of .html
  python3 tools/distinct.py sites/ --pairs 15 --threshold 0.30

Templated sameness is invisible from the inside — every site looks fine on
its own screen. It is obvious from the outside, where a person or a
crawler sees the set. This measures the set.

Four independent signals, because they fail differently:

  copy       8-word shingles, Jaccard. Catches one paragraph reused with
             the nouns swapped — the thing a human reviewer calls spam.
  structure  the block-tag sequence, Jaccard over 5-grams. Two sites can
             share a skeleton honestly; sharing skeleton AND copy is the
             problem.
  headings   h1/h2 text reduced to its shape, so "Three hundred seats,
             one box office" and "Thirty-nine bedrooms, one front door"
             register as the same sentence pattern.
  assets     images and embedded fonts by content hash. A shared logo is
             fine; a shared hero photograph means neither site has one.

High structural similarity with low copy similarity is a design system
working correctly. High copy similarity is the failure, whatever the
structure does.

Stdlib only. No network.
"""
import argparse, hashlib, os, re, sys
from itertools import combinations

RE_SCRIPT = re.compile(r"<script[^>]*>.*?</script>", re.I | re.S)
RE_STYLE = re.compile(r"<style[^>]*>.*?</style>", re.I | re.S)
RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
RE_TAG = re.compile(r"<([a-zA-Z][\w-]*)")
RE_HEAD = re.compile(r"<h([12])\b[^>]*>(.*?)</h\1>", re.I | re.S)
RE_IMG = re.compile(r"<img\b[^>]*src\s*=\s*[\"']([^\"']+)", re.I)
RE_B64 = re.compile(r"base64,([A-Za-z0-9+/=]{200,})")

# Block-level elements only: the page's skeleton, not its inline texture.
BLOCK = {"header", "nav", "main", "section", "article", "aside", "footer", "div",
         "h1", "h2", "h3", "h4", "ul", "ol", "li", "table", "thead", "tbody", "tr",
         "th", "td", "form", "fieldset", "figure", "figcaption", "details", "dialog",
         "blockquote", "p", "canvas", "video", "picture"}

STOP = set("a an the and or but of to in on at for with from by as is are was were be "
           "been it its this that these those you your we our us they their he she his "
           "her not no so if then than there here what which who whom when where how all "
           "can will just about into over under more most other some such only own same".split())


def text_of(html):
    h = RE_COMMENT.sub(" ", html)
    h = RE_SCRIPT.sub(" ", h)
    h = RE_STYLE.sub(" ", h)
    h = h[h.find("<body"):] if "<body" in h else h
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"&[a-z]+;|&#\d+;", " ", h)
    return re.sub(r"\s+", " ", h).strip().lower()


def words(t):
    return [w for w in re.findall(r"[a-z']{2,}", t) if w not in STOP]


def shingles(seq, k):
    return {" ".join(seq[i:i + k]) for i in range(max(0, len(seq) - k + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def heading_shape(t):
    """Reduce a heading to its sentence pattern.

    Words become W, numbers N; stopwords and punctuation stay. Two
    headlines built from one formula collapse to the same string.
    """
    out = []
    for tok in re.findall(r"[a-zA-Z']+|\d[\d,.]*|[·,—–-]", t.lower()):
        if tok in STOP or not tok.isalnum():
            out.append(tok)
        elif tok[0].isdigit():
            out.append("N")
        else:
            out.append("W")
    return " ".join(out)


def profile(name, files):
    copy_words, struct, heads, assets = [], [], [], set()
    titles, descs = [], []
    for path in files:
        html = open(path, encoding="utf-8", errors="replace").read()
        t = text_of(html)
        copy_words += words(t)
        struct += [g.lower() for g in RE_TAG.findall(html) if g.lower() in BLOCK]
        for _, h in RE_HEAD.findall(html):
            clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
            if clean:
                heads.append(heading_shape(clean))
        for src in RE_IMG.findall(html):
            if not src.startswith("data:"):
                p = os.path.normpath(os.path.join(os.path.dirname(path), src.split("?")[0]))
                if os.path.isfile(p):
                    assets.add(hashlib.sha256(open(p, "rb").read()).hexdigest()[:16])
        for b in RE_B64.findall(html):
            assets.add(hashlib.sha256(b.encode()).hexdigest()[:16])
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if m:
            titles.append(" ".join(m.group(1).split()))
        m = re.search(r'name="description"\s+content="([^"]*)"', html)
        if m:
            descs.append(m.group(1))
    return {
        "name": name, "pages": len(files),
        "copy": shingles(copy_words, 8),
        "struct": shingles(struct, 5),
        "heads": set(heads),
        "assets": assets,
        "titles": titles, "descs": descs,
        "n_words": len(copy_words),
    }


def collect(root):
    """A folder of site-folders, or a flat folder treated as one site."""
    sites = []
    subs = [d for d in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, d))]
    for d in subs:
        p = os.path.join(root, d)
        files = [os.path.join(dp, f) for dp, _, fs in os.walk(p)
                 for f in sorted(fs) if f.endswith((".html", ".htm"))]
        if files:
            sites.append((d, files))
    if not sites:
        files = [os.path.join(root, f) for f in sorted(os.listdir(root)) if f.endswith((".html", ".htm"))]
        for f in files:
            sites.append((os.path.splitext(os.path.basename(f))[0], [f]))
    return sites


def bar(v, w=18):
    n = int(round(v * w))
    return "█" * n + "·" * (w - n)


def main():
    ap = argparse.ArgumentParser(description="Measure sameness across a set of sites.")
    ap.add_argument("root")
    ap.add_argument("--threshold", type=float, default=0.30,
                    help="copy-overlap above this is flagged (default 0.30)")
    ap.add_argument("--pairs", type=int, default=12, help="worst pairs to print")
    args = ap.parse_args()

    sites = collect(args.root)
    if len(sites) < 2:
        sys.exit("need at least two sites to compare")
    profs = [profile(n, f) for n, f in sites]

    print("  %-34s %6s %8s" % ("site", "pages", "words"))
    for p in profs:
        print("  %-34s %6d %8d" % (p["name"][:34], p["pages"], p["n_words"]))
    print()

    rows = []
    for a, b in combinations(profs, 2):
        rows.append((jaccard(a["copy"], b["copy"]),
                     jaccard(a["struct"], b["struct"]),
                     jaccard(a["heads"], b["heads"]),
                     jaccard(a["assets"], b["assets"]),
                     a["name"], b["name"]))
    rows.sort(reverse=True)

    print("  Worst pairs by copy overlap")
    print("  %-22s %-22s %8s %9s %8s %7s" % ("site", "site", "copy", "structure", "heads", "assets"))
    for c, s, h, x, an, bn in rows[:args.pairs]:
        flag = "  <-- FLAG" if c >= args.threshold else ""
        print("  %-22s %-22s %7.0f%% %8.0f%% %7.0f%% %6.0f%%%s"
              % (an[:22], bn[:22], c * 100, s * 100, h * 100, x * 100, flag))
    print()

    n = len(rows)
    avg_c = sum(r[0] for r in rows) / n
    avg_s = sum(r[1] for r in rows) / n
    avg_h = sum(r[2] for r in rows) / n
    print("  Set averages over %d pairs" % n)
    print("    copy       %s %5.1f%%" % (bar(avg_c), avg_c * 100))
    print("    structure  %s %5.1f%%" % (bar(avg_s), avg_s * 100))
    print("    headings   %s %5.1f%%" % (bar(avg_h), avg_h * 100))
    print()

    # Repeated headline formulas across the set.
    shapes = {}
    for p in profs:
        for h in p["heads"]:
            shapes.setdefault(h, set()).add(p["name"])
    reused = sorted(((len(v), k) for k, v in shapes.items() if len(v) > 1), reverse=True)
    if reused:
        print("  Headline formulas reused across sites")
        for cnt, shape in reused[:8]:
            print("    %2d sites  %s" % (cnt, shape[:78]))
        print()

    # Title / description built from one string with a slot swapped.
    def common_affix(strings, head=True):
        if len(strings) < 2:
            return ""
        ref = strings[0]
        out = ""
        for i in range(1, len(ref) + 1):
            piece = ref[:i] if head else ref[-i:]
            if all((s.startswith(piece) if head else s.endswith(piece)) for s in strings):
                out = piece
            else:
                break
        return out

    all_titles = [t for p in profs for t in p["titles"]]
    for label, vals in (("title", all_titles), ("description", [d for p in profs for d in p["descs"]])):
        pre, suf = common_affix(vals), common_affix(vals, head=False)
        if len(pre) > 12 or len(suf) > 12:
            print("  Shared %s template detected:" % label)
            if len(pre) > 12:
                print("    every %s starts with %r" % (label, pre[:60]))
            if len(suf) > 12:
                print("    every %s ends with   %r" % (label, suf[:60]))
            print()

    flagged = [r for r in rows if r[0] >= args.threshold]
    print("  %d of %d pairs over the %.0f%% copy threshold" % (len(flagged), n, args.threshold * 100))
    if flagged:
        print("  These read as one site with the nouns changed. Fix by adding facts")
        print("  only that business has — not by rewording. See docs/BUILD-PROTOCOL.md.")
        sys.exit(1)
    print("  PASS — the set carries real per-site difference.")


if __name__ == "__main__":
    main()
