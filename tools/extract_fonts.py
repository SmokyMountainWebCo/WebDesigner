#!/usr/bin/env python3
"""Pull embedded @font-face rules out of an existing HTML page.

  python3 tools/extract_fonts.py existing-page.html > fonts.css

Writes one @font-face{...} block per line, the format build.py expects.
Only extracts faces whose src is a data: URI (already self-contained);
faces that reference external URLs are skipped with a note to stderr, since
they'd break the "works from anywhere" guarantee. Stdlib only.
"""
import re, sys

def main():
    if len(sys.argv) != 2:
        sys.exit("usage: extract_fonts.py page.html > fonts.css")
    html = open(sys.argv[1], encoding="utf-8").read()

    faces = re.findall(r"@font-face\s*\{[^}]*\}", html, re.I)
    if not faces:
        sys.exit("no @font-face rules found in " + sys.argv[1])

    kept, skipped = [], 0
    for f in faces:
        one = re.sub(r"\s+", " ", f).strip()
        if "url(data:" in one:
            kept.append(one)
        else:
            skipped += 1

    if skipped:
        sys.stderr.write("skipped %d face(s) with non-embedded (external URL) src\n" % skipped)
    if not kept:
        sys.exit("found @font-face rules, but none were self-contained data: URIs")

    sys.stdout.write("\n".join(kept) + "\n")
    sys.stderr.write("extracted %d embedded font face(s)\n" % len(kept))

if __name__ == "__main__":
    main()
