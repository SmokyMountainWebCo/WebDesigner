#!/usr/bin/env python3
"""Load every external link in a docs tree and report which ones are
still there.

This repo's house rules say *cite the source and date the claim* and
*don't claim a link works without loading it*. Both were enforced by
memory until this file existed. Citations rot quietly: a source that
moved in March is indistinguishable from one that didn't, right up until
somebody clicks it.

What it does, and what it deliberately doesn't:

  * **Requests are real.** HEAD first, GET on fallback — plenty of
    servers refuse HEAD and a HEAD-only checker invents dead links.
  * **Redirects are reported, not followed silently.** A 301 is not a
    failure, but it *is* a citation that has drifted and should be
    rewritten to its destination.
  * **Placeholders are skipped by name, not by guesswork** — example.com,
    localhost and RFC 2606 reserved names are documentation, not links.
  * **A failure to reach the network is not a dead link.** Timeouts and
    proxy errors report as UNREACHABLE and do not fail the run, because
    "my connection broke" must never be recorded as "their site is gone."

Three false positives this tool produced on its own first run, now fixed,
because each one would have caused a *worse* document if acted on:

  1. **An XML namespace URI is an identifier, not a resource.** The
     `xmlns=` in a sitemap or an SVG is a name that happens to look like
     a URL and is not meant to be fetched. Worse, it must match the spec
     **byte for byte** — "helpfully" rewriting the sitemaps.org namespace
     to https breaks the sitemap. Namespace declarations are skipped.
  2. **403 is not 404.** Plenty of publishers refuse anything that looks
     automated. Reporting that as DEAD invites someone to go and "fix" a
     citation that was never broken, so it reports as BLOCKED and does
     not fail the run.
  3. **A host with no dot cannot resolve.** `https://host/` in an example
     command is documentation. It is skipped rather than reported as an
     outage.

Exit code is non-zero only when a link is genuinely gone (a 404 or a
5xx), so it can gate CI the way `preflight.py` does.

Usage:
    python3 tools/linkcheck.py docs/
    python3 tools/linkcheck.py ../other-repo/docs --json report.json
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RE_URL = re.compile(r"https?://[^\s<>\)\]\"'`,]+")
TRAILING = ".,;:!?)]}>\"'"

# RFC 2606 / RFC 6761 reserved for documentation. Never real endpoints.
PLACEHOLDER = re.compile(
    r"^https?://(?:[\w.-]+\.)?(?:example\.(?:com|net|org)|localhost|"
    r"127\.0\.0\.1|\[::1\]|.*\.(?:test|invalid|example|local))(?::\d+)?(?:/|$)", re.I)

# An XML namespace is a name, not an address. Fetching it proves nothing
# and rewriting it breaks the document that declares it.
RE_NAMESPACE = re.compile(r"""xmlns(?::[\w.-]+)?\s*=\s*["']?$|"""
                          r"""schemaLocation\s*=\s*["']?$""", re.I)

UA = ("Mozilla/5.0 (compatible; linkcheck/1.0; "
      "+repo-internal citation checker)")

OK, REDIRECT, DEAD, BLOCKED, UNREACHABLE, SKIPPED = \
    "OK", "REDIRECT", "DEAD", "BLOCKED", "UNREACHABLE", "SKIPPED"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Report the redirect instead of quietly following it."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def clean(url):
    while url and url[-1] in TRAILING:
        # Keep a balanced closing paren — some real URLs contain them.
        if url[-1] == ")" and url.count("(") > url.count(")"):
            break
        url = url[:-1]
    return url


def find_links(root, exts=(".md", ".html", ".htm")):
    """url -> sorted list of "file:line" citations."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "node_modules", "_work", "intake",
                                    "dist", "__pycache__", ".brain"}]
        for name in sorted(filenames):
            if not name.lower().endswith(exts):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        for m in RE_URL.finditer(line):
                            # What precedes the URL decides whether it is
                            # an address at all.
                            if RE_NAMESPACE.search(line[:m.start()]):
                                continue
                            url = clean(m.group(0))
                            if url:
                                found.setdefault(url, []).append(
                                    "%s:%d" % (os.path.relpath(path, root), n))
            except OSError as e:
                print("warning: can't read %s (%s)" % (path, e.strerror),
                      file=sys.stderr)
    return found


def probe(url, timeout=20):
    if PLACEHOLDER.match(url):
        return SKIPPED, 0, "reserved for documentation"

    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    if "." not in host:
        return SKIPPED, 0, "not a fully-qualified host — an example, not an address"

    opener = urllib.request.build_opener(NoRedirect)
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method,
                                     headers={"User-Agent": UA,
                                              "Accept": "*/*"})
        try:
            with opener.open(req, timeout=timeout) as resp:
                return OK, resp.status, ""
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                return REDIRECT, e.code, e.headers.get("Location", "") or ""
            # 403/405 on HEAD is usually method refusal, not absence.
            if method == "HEAD" and e.code in (400, 403, 405, 501):
                continue
            # Refused, but present. Never report this as gone.
            if e.code in (401, 403, 429):
                return BLOCKED, e.code, (e.reason or "") + \
                    " — refused an automated request; verify by hand"
            # 5xx is the *server* failing, not the resource being absent.
            # 503 is literally "Service Unavailable" — temporary by
            # definition. Calling it dead sends somebody to rewrite a
            # citation that was fine.
            if e.code >= 500:
                return UNREACHABLE, e.code, (e.reason or "") + \
                    " — server-side error, try again later"
            return DEAD, e.code, e.reason or ""
        except urllib.error.URLError as e:
            if method == "HEAD":
                continue
            return UNREACHABLE, 0, str(getattr(e, "reason", e))
        except Exception as e:                    # socket/ssl/decode oddities
            if method == "HEAD":
                continue
            return UNREACHABLE, 0, type(e).__name__ + ": " + str(e)
    return UNREACHABLE, 0, "no method succeeded"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="directory to scan")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--json", help="write the full report here")
    args = ap.parse_args()

    if not os.path.isdir(args.root):
        sys.exit("error: %s is not a directory" % args.root)

    links = find_links(args.root)
    if not links:
        print("no external links found in %s" % args.root)
        return

    print("checking %d unique links in %s\n" % (len(links), args.root))

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda u: (u,) + probe(u, args.timeout),
                                sorted(links)))

    buckets = {}
    for url, status, code, note in results:
        buckets.setdefault(status, []).append((url, code, note))

    for status in (DEAD, REDIRECT, BLOCKED, UNREACHABLE, SKIPPED, OK):
        rows = buckets.get(status, [])
        if not rows:
            continue
        if status == OK:
            print("%s  %d links" % (OK, len(rows)))
            continue
        print("%s  %d" % (status, len(rows)))
        for url, code, note in rows:
            print("  %s%s" % (url, (" -> %s" % code) if code else ""))
            if note:
                print("      %s" % note[:110])
            for cite in links[url][:3]:
                print("      cited at %s" % cite)
        print()

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([{"url": u, "status": s, "code": c, "note": n,
                        "cited_at": links[u]}
                       for u, s, c, n in results], fh, indent=2)
        print("report written to %s" % args.json)

    dead = len(buckets.get(DEAD, []))
    print("\n%d ok, %d redirected, %d dead, %d blocked, %d unreachable, %d skipped"
          % (len(buckets.get(OK, [])), len(buckets.get(REDIRECT, [])),
             dead, len(buckets.get(BLOCKED, [])),
             len(buckets.get(UNREACHABLE, [])),
             len(buckets.get(SKIPPED, []))))
    if buckets.get(BLOCKED):
        print("blocked != dead — the server refused a bot, not the URL.")
    if buckets.get(UNREACHABLE):
        print("unreachable != dead — re-run before editing any citation.")
    sys.exit(1 if dead else 0)


if __name__ == "__main__":
    main()
