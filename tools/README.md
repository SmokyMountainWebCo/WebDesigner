# The toolchain

Three small programs. No `package.json`, no lockfile, no framework. Python
stdlib only for the build; Playwright for the optional QA pass.

```
build.py           config + fonts + template  ->  one self-contained HTML file
extract_fonts.py   any page with embedded fonts -> fonts.css
check.js           a built page -> pass/fail + three screenshots
```

## The workflow

**1 · Copy the config and fill it in.**

```bash
cp template/config.example.json config.json
```

Every `{{TOKEN}}` in the template gets a value here. The build **fails
loudly** on any token you missed — that's deliberate, an unresolved
`{{PAGE_TITLE}}` in a shipped page is worse than a build error.

**2 · Write the copy.** Duplicate `template/page-template.html`, or edit
in place, replacing each `[BRACKET PROMPT]`. Each prompt states the job of
the passage that replaces it. The build **warns but does not fail** on
leftover prompts, so early drafts still build.

**3 · Prepare fonts (optional).**

```bash
# From a page that already has them embedded:
python3 tools/extract_fonts.py existing-page.html > fonts.css

# From raw woff2 files: subset first, then base64 one @font-face per line.
# Format and subsetting commands: template/fonts.css.example
#                                 docs/OPEN-SOURCE.md
```

Skip this entirely and the page falls back to Georgia and the system
monospace — it still looks intentional, because the fallback stack was
chosen rather than defaulted.

**4 · Build.**

```bash
python3 tools/build.py template/page-template.html \
    -c config.json -f fonts.css -o dist/page.html
```

Both `-c` and `-f` are optional. Output is a single file with no external
requests of any kind.

**5 · Verify.**

```bash
node tools/check.js dist/page.html
```

Checks that no console or page errors fired, that the background canvas is
still displayed (**a shader compile error hides it and is otherwise
completely silent** — this is the check that earns the harness its keep),
and that no `{{TOKENS}}` survived. Reports the sections, headings, and
outbound links it found, then drops three screenshots beside the input at
scroll depths 0 / mid / end so you can see the scene's arc.

Requires Playwright with a Chromium. If your Chromium is at a fixed path:

```bash
CHROMIUM_PATH=/path/to/chrome node tools/check.js dist/page.html
```

**6 · Deploy.** It's one file. Any static host, any bucket, an email
attachment, a thumb drive. If it should stay out of search results, leave
the `noindex` meta in place and link it only from where you choose —
remembering that **unlisted is not private**: anyone with the URL can open
it, which is exactly what makes a shared link work.

If it *should* be indexed, delete the `noindex` line and see
`docs/MASTERING-THE-INTERNET.md` for the tag set that makes a link preview
render and a page get crawled.

## Why it's built this way

| Choice | Reason |
|---|---|
| Python stdlib only | Works on any machine with `python3`. Nothing to install, nothing to update, nothing to audit |
| Fails on unresolved tokens | A template artifact in a shipped page is the one error nobody catches by reading |
| Warns on unwritten prompts | Drafts must still build, or you stop using the tool |
| Rejects non-embedded fonts | `extract_fonts.py` skips faces with external URLs — they'd break the "works from anywhere" guarantee |
| Headless QA is separate | The build shouldn't require Node or a browser. Verification is a distinct step you can skip while drafting |
| Screenshots, not assertions | Nobody can write an assertion for "the sky looks right." Three images and two seconds of looking does it |

## Extending it

The build is 57 lines of string substitution. If you need partials, loops,
or a multi-page site, that's the point at which a real generator earns its
keep — Eleventy, Astro, Hugo, or Zola (`docs/OPEN-SOURCE.md`). Don't grow
this script into a template language; it's deliberately the smallest thing
that produces one correct file.

Worth adding when you need it, in rough order of payoff:

- **OG image generation** — render an HTML card at 1200×630 headlessly to
  PNG. `check.js` already has the screenshot mechanics; it's about ten
  lines.
- **A link checker** — `check.js` already collects every outbound href;
  fetching each one and asserting a 200 is a small addition, and a dead
  link in a shipped page is embarrassing in a way nothing else is.
- **An `axe-core` pass** — inject the script, run it, fail the build on
  serious violations.
- **Brotli pre-compression** of the output, if you're serving it yourself
  rather than from a CDN that does it for you.
