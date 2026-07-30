#!/usr/bin/env python3
"""Extract reusable technique out of saved HTML pages.

  python3 tools/harvest.py _work/manifest.json -o _work/harvest
  python3 tools/harvest.py some-page.html            # one file, straight to stdout

Reads pages and pulls out the parts that are *transferable* — palette,
design tokens, type and spacing scales, which platform features the page
uses, what it depends on from other origins, inline shaders, and its
accessibility and weight signals. Writes one JSON per page plus a corpus
report that ranks what's worth keeping.

It deliberately does not extract copy, images, names, or anything else
that belongs to whoever wrote the page. What comes out is measurements
and method. See docs/INTAKE.md for the provenance and license gate that
governs what may then graduate into library/.

Stdlib only, regex-based: this reads minified and hand-written CSS alike
without needing a parser, and never executes anything.
"""
import argparse, json, os, re, sys
from collections import Counter
from urllib.parse import unquote
from datetime import datetime, timezone

# ── extraction patterns ───────────────────────────────────────────────────
RE_TITLE   = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
RE_META    = re.compile(r"<meta\s+([^>]+?)/?>", re.I)
RE_ATTR    = re.compile(r"""([a-zA-Z:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
RE_LANG    = re.compile(r"<html[^>]*\blang\s*=\s*[\"']([^\"']+)", re.I)
RE_JSONLD  = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.I | re.S)
RE_STYLE   = re.compile(r"<style[^>]*>(.*?)</style>", re.I | re.S)
RE_SCRIPT  = re.compile(r"<script(?![^>]+application/ld\+json)[^>]*>(.*?)</script>", re.I | re.S)
RE_LINKTAG = re.compile(r"<link\s+([^>]+?)/?>", re.I)
RE_SCRIPTTAG = re.compile(r"<script\s+([^>]*?src\s*=[^>]*?)/?>", re.I)
# Tags whose src/href causes the browser to fetch something.
RE_FETCHTAG = re.compile(r"<(script|link|img|iframe|video|audio|source|track|embed|object|use)\s+([^>]+?)/?>", re.I)
FETCHING_REL = {"stylesheet", "preload", "prefetch", "preconnect", "dns-prefetch",
                "modulepreload", "icon", "apple-touch-icon", "manifest", "prerender"}

RE_HEX     = re.compile(r"#([0-9a-fA-F]{3,8})\b")
RE_RGB     = re.compile(r"\brgba?\(\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)", re.I)
RE_HSL     = re.compile(r"\bhsla?\(\s*([\d.]+)(?:deg)?\s*[, ]\s*([\d.]+)%\s*[, ]\s*([\d.]+)%", re.I)
RE_OKLCH   = re.compile(r"\bokl(?:ch|ab)\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)", re.I)
RE_VARDEF  = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;{}]+)")
RE_FONTFACE= re.compile(r"@font-face\s*\{([^}]*)\}", re.I)
RE_FAMILY  = re.compile(r"font-family\s*:\s*([^;{}]+)", re.I)
RE_FSIZE   = re.compile(r"font-size\s*:\s*([^;{}]+)", re.I)
RE_SPACE   = re.compile(r"(?:margin|padding|gap|row-gap|column-gap)[a-z-]*\s*:\s*([^;{}]+)", re.I)
RE_LEN     = re.compile(r"(-?[\d.]+)(rem|em|px|ch|vh|vw|svh|dvh|%)")
RE_CSSURL  = re.compile(r"url\(\s*['\"]?([^'\")]+)", re.I)
RE_IMPORT  = re.compile(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", re.I)
RE_IMG     = re.compile(r"<img\b([^>]*)>", re.I | re.S)
RE_HEAD    = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.I | re.S)
RE_INPUT   = re.compile(r"<(input|select|textarea)\b([^>]*)>", re.I)
RE_LABEL   = re.compile(r"<label\b([^>]*)>", re.I)
RE_B64     = re.compile(r"base64,([A-Za-z0-9+/=]{64,})")

# Platform features worth knowing a page uses. Name -> pattern.
TECHNIQUES = [
    ("css-grid",             r"display\s*:\s*grid"),
    ("flexbox",              r"display\s*:\s*flex"),
    ("clamp()",              r"\bclamp\s*\("),
    ("min()/max()",          r"\b(?:min|max)\s*\([^)]*,"),
    ("custom-properties",    r"--[a-zA-Z0-9_-]+\s*:"),
    ("oklch/oklab",          r"\bokl(?:ch|ab)\("),
    ("color-mix()",          r"color-mix\s*\("),
    ("container-queries",    r"@container\b"),
    (":has()",               r":has\s*\("),
    (":focus-visible",       r":focus-visible"),
    ("aspect-ratio",         r"aspect-ratio\s*:"),
    ("backdrop-filter",      r"backdrop-filter\s*:"),
    ("content-visibility",   r"content-visibility\s*:"),
    ("scroll-driven-anim",   r"animation-timeline\s*:|@scroll-timeline|\bview\s*\(\s*\)"),
    ("view-transitions",     r"view-transition|::view-transition"),
    ("logical-properties",   r"(?:margin|padding|inset|border)-(?:block|inline)\b"),
    ("dvh/svh units",        r"\b\d[\d.]*(?:dvh|svh|lvh)\b"),
    ("text-wrap:balance",    r"text-wrap\s*:\s*(?:balance|pretty)"),
    ("prefers-reduced-motion", r"prefers-reduced-motion"),
    ("prefers-color-scheme", r"prefers-color-scheme"),
    ("dark-mode-attr",       r"\[data-theme|:root\[data-"),
    ("@supports",            r"@supports\b"),
    ("variable-font",        r"font-variation-settings|woff2-variations|font-weight\s*:\s*\d+\s+\d+"),
    ("font-display",         r"font-display\s*:"),
    ("tabular-nums",         r"font-variant-numeric\s*:\s*[^;]*tabular"),
    ("embedded-fonts",       r"@font-face[^}]*url\(\s*['\"]?data:"),
    ("webgl-shader",         r"gl_FragColor|precision\s+(?:highp|mediump)\s+float|createShader|WEBGL|getContext\(['\"]webgl"),
    ("canvas-2d",            r"getContext\(\s*['\"]2d"),
    ("svg-inline",           r"<svg\b"),
    ("IntersectionObserver", r"IntersectionObserver"),
    ("ResizeObserver",       r"ResizeObserver"),
    ("requestAnimationFrame",r"requestAnimationFrame"),
    ("<dialog>",             r"<dialog\b"),
    ("popover",              r"\bpopover\s*="),
    ("<details>",            r"<details\b"),
    ("loading=lazy",         r"loading\s*=\s*['\"]?lazy"),
    ("fetchpriority",        r"fetchpriority\s*="),
    ("preload/preconnect",   r"rel\s*=\s*['\"]?(?:preload|preconnect|dns-prefetch|modulepreload)"),
    ("srcset/picture",       r"\bsrcset\s*=|<picture\b"),
    ("json-ld",              r"application/ld\+json"),
    ("open-graph",           r"property\s*=\s*['\"]og:"),
    ("service-worker",       r"serviceWorker"),
    ("web-components",       r"customElements\.define"),
    ("es-modules",           r"type\s*=\s*['\"]module"),
]
TECHNIQUES = [(n, re.compile(p, re.I)) for n, p in TECHNIQUES]

# Anti-patterns the repo has opinions about (README, DESIGN-LOOPHOLES).
FLAGS = [
    ("zoom-disabled",        r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?![\d.])"),
    ("outline:none",         r"outline\s*:\s*(?:none|0)\b"),
    ("!important",           r"!important"),
    ("fixed-100vh",          r"(?:height|min-height)\s*:\s*100vh"),
    ("will-change",          r"will-change\s*:"),
    ("document.write",       r"document\.write"),
    ("jquery",               r"jquery"),
    ("float-layout",         r"\bfloat\s*:\s*(?:left|right)"),
    ("px-font-size",         r"font-size\s*:\s*\d+px"),
    ("table-layout",         r"<table[^>]*>(?![^<]*</table>)"),
]
FLAGS = [(n, re.compile(p, re.I)) for n, p in FLAGS]

NAMED_SKIP = {"none", "inherit", "initial", "unset", "transparent", "currentcolor", "auto"}


def hex_norm(h):
    """Normalize a hex color body to #rrggbb, dropping alpha. None if unusable."""
    h = h.lower()
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    elif len(h) in (6, 8):
        h = h[:6]
    else:
        return None
    return "#" + h


def luminance(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def attrs(s):
    out = {}
    for m in RE_ATTR.finditer(s):
        out[m.group(1).lower()] = m.group(2) or m.group(3) or m.group(4) or ""
    return out


def origin_of(url):
    m = re.match(r"(?:https?:)?//([^/]+)", url.strip())
    return m.group(1).lower() if m else None


def read_text(path):
    raw = open(path, "rb").read()
    try:
        return raw.decode("utf-8"), len(raw)
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace"), len(raw)


def local_target(ref, base_dir):
    """Resolve a page-relative asset reference to a real file, or None.

    Browsers save a page as `Page Title.html` plus a `Page Title_files/`
    folder, so the CSS that holds every color, token and technique lives
    beside the markup rather than in it. Absolute URLs, protocol-relative
    URLs, data: URIs and site-root paths can't be resolved from disk and
    are skipped — which also means this never reaches outside the folder
    the page was saved into.
    """
    ref = ref.strip().split("#")[0].split("?")[0]
    if not ref or ref.startswith(("data:", "//", "/", "\\")) or re.match(r"^[a-zA-Z][\w+.-]*:", ref):
        return None
    cand = os.path.normpath(os.path.join(base_dir, unquote(ref)))
    return cand if os.path.isfile(cand) else None


def gather_linked(text, base_dir, depth=1):
    """Pull in stylesheets and scripts the page links to from its own folder."""
    css_files, js_files, missing = [], [], []
    css_text, js_text = [], []

    for tag in RE_LINKTAG.findall(text):
        a = attrs(tag)
        rel = a.get("rel", "").lower()
        if "stylesheet" not in rel or not a.get("href"):
            continue
        target = local_target(a["href"], base_dir)
        if not target:
            if not re.match(r"^(?:https?:)?//", a["href"].strip()):
                missing.append(a["href"])
            continue
        body, nbytes = read_text(target)
        css_files.append({"path": os.path.relpath(target, base_dir), "bytes": nbytes})
        css_text.append(body)
        # One level of @import, which saved pages and font sheets lean on.
        if depth > 0:
            for imp in RE_IMPORT.findall(body):
                sub = local_target(imp, os.path.dirname(target))
                if sub:
                    sbody, sbytes = read_text(sub)
                    css_files.append({"path": os.path.relpath(sub, base_dir), "bytes": sbytes})
                    css_text.append(sbody)

    for tag in RE_SCRIPTTAG.findall(text):
        a = attrs(tag)
        if not a.get("src"):
            continue
        target = local_target(a["src"], base_dir)
        if not target:
            continue
        body, nbytes = read_text(target)
        js_files.append({"path": os.path.relpath(target, base_dir), "bytes": nbytes})
        js_text.append(body)

    return "\n".join(css_text), "\n".join(js_text), css_files, js_files, missing


def harvest(path, follow_local=True):
    text, raw_bytes = read_text(path)
    base_dir = os.path.dirname(os.path.abspath(path))

    styles = "\n".join(RE_STYLE.findall(text))
    scripts = "\n".join(RE_SCRIPT.findall(text))
    inline_css_len, inline_js_len = len(styles), len(scripts)

    # A saved page keeps its CSS in a sidecar folder. Without this the page
    # harvests as empty — no palette, no tokens, no techniques.
    linked_css = linked_js = ""
    css_files, js_files, missing_refs = [], [], []
    if follow_local:
        linked_css, linked_js, css_files, js_files, missing_refs = gather_linked(text, base_dir)
        styles += "\n" + linked_css
        scripts += "\n" + linked_js
        # Technique and flag detection scans the whole document, so the
        # linked material has to be part of it.
        text = text + "\n<style>" + linked_css + "</style>\n<script>" + linked_js + "</script>"
    # Inline style="" attributes count as CSS for palette purposes.
    css = styles + "\n" + "\n".join(
        m.group(1) or m.group(2) or "" for m in
        re.finditer(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", text)
    )

    # ── palette ──────────────────────────────────────────────────────────
    colors = Counter()
    for m in RE_HEX.finditer(css):
        n = hex_norm(m.group(1))
        if n:
            colors[n] += 1
    rgb_hits = [("rgb(%s,%s,%s)" % m.groups()) for m in RE_RGB.finditer(css)]
    hsl_hits = [("hsl(%s,%s%%,%s%%)" % m.groups()) for m in RE_HSL.finditer(css)]
    oklch_hits = [("oklch(%s %s %s)" % m.groups()) for m in RE_OKLCH.finditer(css)]

    ranked = colors.most_common()
    darks = [c for c, _ in ranked if luminance(c) < 0.2]
    lights = [c for c, _ in ranked if luminance(c) > 0.75]
    mids = [c for c, _ in ranked if 0.2 <= luminance(c) <= 0.75]

    # ── tokens ───────────────────────────────────────────────────────────
    tokens = {}
    for name, val in RE_VARDEF.findall(css):
        val = " ".join(val.split())
        tokens.setdefault(name, val)

    # ── type + spacing scales ────────────────────────────────────────────
    def scale_from(pattern, blob):
        vals = Counter()
        for decl in pattern.findall(blob):
            for num, unit in RE_LEN.findall(decl):
                try:
                    f = float(num)
                except ValueError:
                    continue
                if f == 0:
                    continue
                vals["%g%s" % (f, unit)] += 1
        return vals

    fsizes = scale_from(RE_FSIZE, css)
    spaces = scale_from(RE_SPACE, css)

    def sort_lengths(counter):
        def key(k):
            m = re.match(r"(-?[\d.]+)(\D+)", k)
            return (m.group(2), float(m.group(1))) if m else ("", 0)
        return sorted(counter.keys(), key=key)

    # ── fonts ────────────────────────────────────────────────────────────
    faces = []
    for block in RE_FONTFACE.findall(css):
        fam = RE_FAMILY.search(block)
        faces.append({
            "family": (fam.group(1).strip().strip("'\"") if fam else "?"),
            "embedded": "url(data:" in block.replace(" ", ""),
            "weight": (re.search(r"font-weight\s*:\s*([^;]+)", block, re.I).group(1).strip()
                       if re.search(r"font-weight\s*:\s*([^;]+)", block, re.I) else None),
            "style": (re.search(r"font-style\s*:\s*([^;]+)", block, re.I).group(1).strip()
                      if re.search(r"font-style\s*:\s*([^;]+)", block, re.I) else None),
            "format": (re.search(r"format\(\s*['\"]?([\w-]+)", block, re.I).group(1)
                       if re.search(r"format\(\s*['\"]?([\w-]+)", block, re.I) else None),
        })
    stacks = Counter()
    for decl in RE_FAMILY.findall(css):
        decl = " ".join(decl.split())
        if "var(" not in decl and decl.lower() not in NAMED_SKIP:
            stacks[decl] += 1

    # ── dependencies on other origins ────────────────────────────────────
    # Only references that actually cause a fetch. An <a href>, a
    # rel=canonical, and an og:url are navigation and metadata — counting
    # them as dependencies inflates the number that's supposed to drive
    # "what should I self-host", and a self-contained page reads as though
    # it had nine third parties.
    refs, link_refs = [], []
    for m in RE_FETCHTAG.finditer(text):
        tag = m.group(1).lower()
        a = attrs(m.group(2))
        if tag == "link":
            rel = a.get("rel", "").lower()
            if not (FETCHING_REL & set(rel.split())):
                continue
            ref = a.get("href")
        else:
            ref = a.get("src") or a.get("srcset", "").split(",")[0].strip().split(" ")[0]
        if ref:
            refs.append(ref)
    for m in re.finditer(r"<a\b([^>]*)>", text, re.I):
        href = attrs(m.group(1)).get("href", "")
        o = origin_of(href)
        if o:
            link_refs.append(o)
    refs += RE_CSSURL.findall(css) + RE_IMPORT.findall(css)
    origins = Counter()
    for r in refs:
        if r.startswith("data:"):
            continue
        o = origin_of(r)
        if o:
            origins[o] += 1
    outbound = Counter(link_refs)

    # ── techniques and flags ─────────────────────────────────────────────
    whole = text
    techniques = sorted(n for n, rx in TECHNIQUES if rx.search(whole))
    flags = {}
    for n, rx in FLAGS:
        hits = len(rx.findall(whole))
        if hits:
            flags[n] = hits

    # ── shaders ──────────────────────────────────────────────────────────
    shaders = []
    if re.search(r"gl_FragColor|gl_Position", scripts):
        for m in re.finditer(r"(precision\s+(?:highp|mediump|lowp)\s+float\s*;.*?)(?=['\"`]\s*\]\s*\.join|</script>|$)",
                             scripts, re.S):
            body = m.group(1)
            shaders.append({
                "chars": len(body),
                "uniforms": sorted(set(re.findall(r"uniform\s+\w+\s+(\w+)", body))),
                "uses_noise": bool(re.search(r"\bfbm\b|\bnoise\b|hash|fract\s*\(", body)),
                "uses_smoothstep": "smoothstep" in body,
                "loops": len(re.findall(r"\bfor\s*\(", body)),
            })
        if not shaders:
            shaders.append({"chars": None, "uniforms": sorted(set(re.findall(r"uniform\s+\w+\s+(\w+)", scripts))),
                            "uses_noise": None, "uses_smoothstep": None, "loops": None})

    # ── accessibility signals ────────────────────────────────────────────
    imgs = [attrs(a) for a in RE_IMG.findall(text)]
    with_alt = sum(1 for a in imgs if "alt" in a)
    sized = sum(1 for a in imgs if ("width" in a and "height" in a) or "aspect-ratio" in a.get("style", ""))
    headings = [int(lvl) for lvl, _ in RE_HEAD.findall(text)]
    skips = sum(1 for a, b in zip(headings, headings[1:]) if b - a > 1)
    inputs = [attrs(a) for _, a in RE_INPUT.findall(text)]
    typed_inputs = [a for a in inputs if a.get("type", "text").lower() not in ("hidden", "submit", "button", "reset")]
    labels = [attrs(a) for a in RE_LABEL.findall(text)]
    label_targets = {a.get("for") for a in labels if a.get("for")}
    labelled = sum(1 for a in typed_inputs
                   if a.get("id") in label_targets or "aria-label" in a or "aria-labelledby" in a)
    vp = ""
    for m in RE_META.finditer(text):
        a = attrs(m.group(1))
        if a.get("name", "").lower() == "viewport":
            vp = a.get("content", "")

    # ── meta / distribution ──────────────────────────────────────────────
    metas, og, twitter = {}, {}, {}
    for m in RE_META.finditer(text):
        a = attrs(m.group(1))
        key = a.get("property") or a.get("name")
        if not key:
            continue
        key = key.lower()
        (og if key.startswith("og:") else twitter if key.startswith("twitter:") else metas)[key] = a.get("content", "")
    ldtypes = []
    for blob in RE_JSONLD.findall(text):
        try:
            data = json.loads(blob)
        except (json.JSONDecodeError, ValueError):
            ldtypes.append("<invalid JSON>")
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and "@type" in node:
                t = node["@type"]
                ldtypes += t if isinstance(t, list) else [t]

    b64 = sum(len(m.group(1)) for m in RE_B64.finditer(text))
    title = RE_TITLE.search(text)
    lang = RE_LANG.search(text)

    return {
        "file": os.path.relpath(path),
        "bytes": raw_bytes,
        "weight": {
            "inline_css_bytes": inline_css_len,
            "inline_js_bytes": inline_js_len,
            "linked_css_bytes": sum(f["bytes"] for f in css_files),
            "linked_js_bytes": sum(f["bytes"] for f in js_files),
            "base64_payload_bytes": b64,
            "markup_bytes": max(0, raw_bytes - inline_css_len - inline_js_len - b64),
            "self_contained": not origins and not css_files and not js_files,
        },
        "linked": {
            "css": css_files,
            "js": js_files,
            "unresolved": missing_refs,
        },
        "meta": {
            "title": (" ".join(title.group(1).split()) if title else None),
            "lang": (lang.group(1) if lang else None),
            "description": metas.get("description"),
            "robots": metas.get("robots"),
            "viewport": vp or None,
            "og_tags": sorted(og),
            "twitter_tags": sorted(twitter),
            "json_ld_types": sorted(set(ldtypes)),
        },
        "palette": {
            "unique_hex": len(colors),
            "top": [{"hex": c, "uses": n} for c, n in ranked[:24]],
            "darks": darks[:8], "mids": mids[:8], "lights": lights[:8],
            "rgb_forms": len(rgb_hits), "hsl_forms": len(hsl_hits), "oklch_forms": len(oklch_hits),
        },
        "tokens": tokens,
        "type_scale": {"values": sort_lengths(fsizes), "most_used": fsizes.most_common(8)},
        "spacing_scale": {"values": sort_lengths(spaces), "most_used": spaces.most_common(10)},
        "fonts": {
            "faces": faces,
            "embedded_faces": sum(1 for f in faces if f["embedded"]),
            "external_faces": sum(1 for f in faces if not f["embedded"]),
            "stacks": stacks.most_common(8),
        },
        "dependencies": {"origins": origins.most_common(), "count": sum(origins.values())},
        "outbound_links": {"origins": outbound.most_common(), "count": sum(outbound.values())},
        "techniques": techniques,
        "flags": flags,
        "shaders": shaders,
        "a11y": {
            "html_lang": bool(lang),
            "images": len(imgs), "with_alt": with_alt, "with_dimensions": sized,
            "headings": headings[:40], "heading_level_skips": skips,
            "inputs": len(typed_inputs), "labelled_inputs": labelled,
            "zoom_disabled": bool(re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?![\d.])", vp)),
        },
    }


# ── corpus report ─────────────────────────────────────────────────────────
def report(results, top):
    n = len(results)
    lines = ["# Harvest report", ""]
    lines.append("**Pages read:** %d · **Generated:** %s" %
                 (n, datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    lines.append("")
    lines.append("Measurements and method only — no copy, no images, no names. Nothing")
    lines.append("here graduates into `library/` until it clears the provenance and")
    lines.append("license gate in `docs/INTAKE.md`.")
    lines.append("")

    # palette across the corpus
    allc = Counter()
    for r in results:
        for c in r["palette"]["top"]:
            allc[c["hex"]] += c["uses"]
    if allc:
        lines += ["## Palette across the corpus", "",
                  "| Color | Uses | Pages | Band |", "|---|---|---|---|"]
        for hexc, uses in allc.most_common(top):
            pages = sum(1 for r in results if any(c["hex"] == hexc for c in r["palette"]["top"]))
            lum = luminance(hexc)
            band = "dark" if lum < 0.2 else "light" if lum > 0.75 else "mid"
            lines.append("| `%s` | %d | %d/%d | %s |" % (hexc, uses, pages, n, band))
        lines.append("")

    # technique adoption
    tech = Counter()
    for r in results:
        tech.update(r["techniques"])
    if tech:
        lines += ["## Techniques in use", "", "| Technique | Pages | |", "|---|---|---|"]
        for name, cnt in tech.most_common():
            bar = "█" * max(1, round(10 * cnt / n))
            lines.append("| %s | %d/%d | %s |" % (name, cnt, n, bar))
        lines.append("")

    # flags
    flg = Counter()
    for r in results:
        flg.update(r["flags"].keys())
    if flg:
        lines += ["## Flags worth reviewing", "",
                  "Not automatically wrong — worth a look. See `docs/DESIGN-LOOPHOLES.md`",
                  "(\"Loopholes that are actually traps\") and `docs/DESIGN.md`.", "",
                  "| Flag | Pages |", "|---|---|"]
        for name, cnt in flg.most_common():
            lines.append("| %s | %d/%d |" % (name, cnt, n))
        lines.append("")

    # dependencies
    deps = Counter()
    for r in results:
        for o, c in r["dependencies"]["origins"]:
            deps[o] += c
    lines += ["## External origins depended on", ""]
    if deps:
        lines += ["Each is a request, a cache entry, a privacy exposure, and a way for",
                  "the page to break later.", "", "| Origin | Refs | Pages |", "|---|---|---|"]
        for o, c in deps.most_common(25):
            pages = sum(1 for r in results if any(x[0] == o for x in r["dependencies"]["origins"]))
            lines.append("| `%s` | %d | %d/%d |" % (o, c, pages, n))
    else:
        lines.append("None — every page read is fully self-contained.")
    lines.append("")

    # fonts
    fams = Counter()
    emb = ext = 0
    for r in results:
        for f in r["fonts"]["faces"]:
            fams[f["family"]] += 1
        emb += r["fonts"]["embedded_faces"]
        ext += r["fonts"]["external_faces"]
    if fams:
        lines += ["## Font faces found", "",
                  "%d embedded (data: URI, self-contained) · %d external." % (emb, ext),
                  "Embedded faces can be recovered with `tools/extract_fonts.py`.",
                  "**Check the license before reusing any of them** — see",
                  "`docs/OPEN-SOURCE.md`.", "", "| Family | Faces |", "|---|---|"]
        for fam, c in fams.most_common(20):
            lines.append("| %s | %d |" % (fam, c))
        lines.append("")

    # scales
    ts, ss = Counter(), Counter()
    for r in results:
        ts.update(dict(r["type_scale"]["most_used"]))
        ss.update(dict(r["spacing_scale"]["most_used"]))
    if ts or ss:
        lines += ["## Scales", ""]
        if ts:
            lines.append("**Type sizes, most used:** " +
                         ", ".join("`%s`(%d)" % (k, v) for k, v in ts.most_common(12)))
            lines.append("")
        if ss:
            lines.append("**Spacing values, most used:** " +
                         ", ".join("`%s`(%d)" % (k, v) for k, v in ss.most_common(14)))
            lines.append("")
        lines.append("A tight, repeating set means a real scale. A long tail of")
        lines.append("one-off values means there wasn't one — see `docs/DESIGN.md`.")
        lines.append("")

    # shaders
    sh = [(r["file"], s) for r in results for s in r["shaders"]]
    if sh:
        lines += ["## Inline shaders", "",
                  "Highest visual-return-per-byte on the platform — see",
                  "`docs/SCROLL-SCENE.md`.", "", "| Page | Chars | Uniforms | noise | smoothstep |",
                  "|---|---|---|---|---|"]
        for f, s in sh:
            lines.append("| `%s` | %s | %s | %s | %s |" % (
                os.path.basename(f), s["chars"] or "?",
                ", ".join(s["uniforms"]) or "—",
                "yes" if s["uses_noise"] else "no",
                "yes" if s["uses_smoothstep"] else "no"))
        lines.append("")

    # distribution + a11y readiness
    lines += ["## Per-page signals", "",
              "| Page | KB | Self-contained | OG | JSON-LD | alt | dims | Techniques |",
              "|---|---|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: -r["bytes"]):
        a = r["a11y"]
        lines.append("| `%s` | %d | %s | %d | %s | %s | %s | %d |" % (
            os.path.basename(r["file"]), round(r["bytes"] / 1000),
            "yes" if r["weight"]["self_contained"] else "no",
            len(r["meta"]["og_tags"]),
            ", ".join(r["meta"]["json_ld_types"]) or "—",
            ("%d/%d" % (a["with_alt"], a["images"])) if a["images"] else "—",
            ("%d/%d" % (a["with_dimensions"], a["images"])) if a["images"] else "—",
            len(r["techniques"])))
    lines.append("")

    # what to do next
    lines += ["## Candidates to graduate", "",
              "Ranked by what usually pays off. Each still needs its source URL and",
              "license recorded in the manifest before anything moves into `library/`.", ""]
    cands = []
    if emb:
        cands.append("**%d embedded font face(s)** — recover with `extract_fonts.py`, "
                     "then verify the license (OFL is reusable; a commercial webfont is not)." % emb)
    if sh:
        cands.append("**%d inline shader(s)** — read against `docs/SCROLL-SCENE.md`; "
                     "the phase-gating and layer math are the transferable part." % len(sh))
    strong = [t for t, c in tech.items() if c >= max(2, n // 2)]
    if strong:
        cands.append("**Consistent technique set** across the corpus: %s — worth writing up "
                     "as a pattern rather than re-deriving each time." % ", ".join(sorted(strong)[:8]))
    if allc:
        cands.append("**A palette of %d recurring colors** — the top 8–12 are a real "
                     "palette; the rest is drift. Record as OKLCH in `library/palettes/`." % len(allc))
    if ts:
        cands.append("**A type scale** — %s. Check whether it's a ratio or an accident."
                     % ", ".join(k for k, _ in ts.most_common(6)))
    if deps:
        cands.append("**%d external origin(s) to eliminate** — each one inlined or "
                     "self-hosted is a request and a failure mode removed." % len(deps))
    if flg:
        cands.append("**%d flag type(s) to review** — fixing these in your own pages is "
                     "the cheapest quality win available." % len(flg))
    lines += ["- " + c for c in cands] if cands else ["Nothing stood out — check the drop folder."]
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Extract reusable technique from saved HTML.")
    ap.add_argument("input", help="a manifest.json from ingest.py, or a single .html file")
    ap.add_argument("-o", "--out", help="output folder (default: print one page to stdout)")
    ap.add_argument("--top", type=int, default=24, help="palette entries in the report (default 24)")
    ap.add_argument("--no-follow", action="store_true",
                    help="don't read stylesheets/scripts the page links to from its own folder")
    args = ap.parse_args()

    if args.input.endswith(".json"):
        manifest = json.load(open(args.input, encoding="utf-8"))
        base = os.path.dirname(os.path.abspath(args.input))
        paths = []
        for i in manifest["items"]:
            if i["kind"] != "page":
                continue
            p = i["path"] if os.path.exists(i["path"]) else os.path.join(base, os.path.basename(i["path"]))
            paths.append(p)
        if not paths:
            sys.exit("no pages in %s — nothing to harvest" % args.input)
    else:
        paths = [args.input]

    results, failed = [], []
    for p in paths:
        try:
            results.append(harvest(p, follow_local=not args.no_follow))
        except (OSError, UnicodeError) as e:
            failed.append((p, str(e)))

    if not results:
        sys.exit("error: nothing could be read" + ("; first failure: %s" % failed[0][1] if failed else ""))

    if not args.out:
        json.dump(results[0] if len(results) == 1 else results, sys.stdout, indent=1)
        sys.stdout.write("\n")
        return

    os.makedirs(args.out, exist_ok=True)
    for r in results:
        stem = re.sub(r"[^\w.-]+", "-", os.path.splitext(os.path.basename(r["file"]))[0])
        with open(os.path.join(args.out, stem + ".json"), "w", encoding="utf-8") as f:
            json.dump(r, f, indent=1)
    with open(os.path.join(args.out, "corpus.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    rpath = os.path.join(args.out, "REPORT.md")
    with open(rpath, "w", encoding="utf-8") as f:
        f.write(report(results, args.top))

    print("harvested %d page(s) -> %s" % (len(results), args.out))
    for p, why in failed:
        print("  unreadable: %s (%s)" % (p, why))
    print("read %s" % rpath)


if __name__ == "__main__":
    main()
