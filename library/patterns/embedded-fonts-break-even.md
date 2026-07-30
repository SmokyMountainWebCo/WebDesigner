# Embedded fonts — where the zero-request page stops paying

    Source:  original
    License: n/a — measurements only
    Date:    2026-07-30
    What:    The measurement that decides whether to base64 fonts into the
             HTML or serve them as one shared file. Reach for it before
             building the second page of a site.

## The technique

Base64 every `@font-face` into the page's inline `<style>`. The page then
has **zero external requests** — it renders identically from a CDN, a
thumb drive, or an email attachment, there is no FOUT because the fonts
arrive with the CSS, and the CSP can be locked to `default-src 'none'`
with `font-src data:`.

It is an excellent trade for **one page**. It stops being one somewhere
around the third.

## The measurement that shows why

A twelve-page corpus of single-file pages, all sharing one type system:

| | |
|---|---|
| Total across all pages | 4.8 MB |
| Of that, font payload | **3.2 MB (66%)** |
| Unique font faces | **7** |
| Those 7 faces, once | 307 KB |
| **Duplicated across pages** | **2.9 MB** |

Per page, the fonts were 56–72% of the file. The pages themselves — markup,
CSS, inline JS, a WebGL shader — were only 90–183 KB.

The break-even is easy to state. With `F` bytes of font and `P` bytes of
page, embedding costs `N × (F + P)` for a visitor who sees `N` pages;
sharing costs `F + N × P` plus one request. Embedding wins only while
`N = 1`. At the numbers above:

| Pages viewed | Embedded | Shared | Saved |
|---|---|---|---|
| 1 | 340 KB | 340 KB + 1 req | — |
| 2 | 700 KB | 445 KB | 36% |
| 3 | 1.1 MB | 550 KB | 50% |
| 5 | 1.9 MB | 760 KB | 60% |

Base64 also inflates: it costs about **33% more bytes** than the binary
woff2, though gzip/brotli claws most of that back on the wire. The
duplication is the real cost, not the encoding.

## The rule

- **One page that must work from anywhere** → embed. A single-page site,
  a pitch, a link you'll email as a file. The zero-request property is
  worth more than the bytes.
- **Two or more pages a visitor might cross** → share one font stylesheet,
  cached a year. Pages 2+ arrive at a third of the weight.

## What sharing costs, stated honestly

It is not free, which is why the decision belongs to whoever owns the site:

- **One extra round trip before text can paint in the real face.** With
  `font-display:swap` you get a visible flash of the fallback; with
  `block` you get briefly invisible text instead. Either is a change to
  what loading *looks like*, even though the settled page is identical.
  Preloading the two or three critical faces shrinks the window but does
  not close it.
- **The CSP has to loosen** from `font-src data:` to `font-src 'self'`.
- **The page stops being one file**, which is a real loss if the site is
  ever handed over, archived, or opened from disk.

Mitigate by subsetting first — often the bigger win and it costs nothing
architecturally. Seven faces at 307 KB is already disciplined; a
Latin-only subset of a display face used for two headings can be under
20 KB.

## How to check a corpus

    python3 tools/harvest.py _work/manifest.json -o _work/harvest

The report's font section lists faces per family and flags embedded vs
external. For the duplication figure, hash each `url(data:…)` payload
across pages and count the repeats — identical hashes across `N` pages
means `(N-1) × size` is being sent for nothing.
