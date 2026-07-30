#!/usr/bin/env python3
"""Assemble a single self-contained HTML page from template + config + fonts.

  python3 tools/build.py template/page-template.html \
      -c config.json -f fonts.css -o dist/page.html

- Substitutes {{TOKENS}} from the JSON config (all values are strings).
- Injects embedded @font-face lines in place of the /*@@FONTS@@*/ marker.
- Fails if any {{TOKEN}} is left unresolved; warns on leftover [BRACKET PROMPTS].

Both -c and -f are optional: with no config the tokens must already be
filled in the template; with no fonts the page falls back to system fonts.
Stdlib only.
"""
import argparse, json, os, re, sys

def main():
    ap = argparse.ArgumentParser(description="Build a one-file page from the template.")
    ap.add_argument("template", help="path to page-template.html")
    ap.add_argument("-c", "--config", help="JSON of {{TOKEN}} -> value")
    ap.add_argument("-f", "--fonts", help="fonts.css with @font-face lines to embed")
    ap.add_argument("-o", "--out", required=True, help="output HTML path")
    args = ap.parse_args()

    html = open(args.template, encoding="utf-8").read()

    if args.fonts:
        fonts = open(args.fonts, encoding="utf-8").read().strip()
        if "/*@@FONTS@@*/" not in html:
            sys.exit("error: template has no /*@@FONTS@@*/ marker to inject fonts into")
        html = html.replace("/*@@FONTS@@*/", fonts)
    else:
        html = html.replace("/*@@FONTS@@*/", "/* no fonts embedded; using system fallbacks */")

    if args.config:
        cfg = json.load(open(args.config, encoding="utf-8"))
        for key, val in cfg.items():
            html = html.replace("{{" + key + "}}", str(val))

    leftover_tokens = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", html)))
    if leftover_tokens:
        sys.exit("error: unresolved tokens: " + ", ".join(leftover_tokens))

    # [BRACKET PROMPTS] are copy placeholders — warn, don't fail (early drafts
    # may legitimately still have some).
    brackets = re.findall(r"\[[A-Z][^\]]{4,}\]", html)
    if brackets:
        sys.stderr.write("warning: %d unwritten copy prompt(s) remain, e.g.:\n" % len(brackets))
        for b in brackets[:5]:
            sys.stderr.write("  " + b[:80] + "\n")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    open(args.out, "w", encoding="utf-8").write(html)
    print("wrote %s (%d bytes)" % (args.out, len(html.encode("utf-8"))))

if __name__ == "__main__":
    main()
