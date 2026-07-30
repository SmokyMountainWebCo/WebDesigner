# Link preview cards — render them from the site's own CSS

    Source:  original
    License: n/a — method only
    Date:    2026-07-30
    What:    Generating 1200×630 Open Graph images as HTML rendered
             headless, so the card is made of the same type and palette as
             the page. Reach for it when a page will be shared in a DM.

## The problem it solves

A page with no `og:image` renders in Slack, iMessage, WhatsApp and every
social product as a bare grey rectangle with a hostname. For a page whose
entire distribution is *someone pasting the link*, the preview card is
the page — it is seen far more often than the site.

Making those cards by hand in a design tool guarantees they drift from
the site's type and color within one redesign. Rendering them from HTML
means they cannot.

## The method

1. **Extract the site's own fonts** so the card uses the real faces:

       python3 tools/extract_fonts.py page.html > og-fonts.css

2. **Write one card template** — a 1200×630 page linking that CSS, with
   the site's own custom properties and empty slots (`kicker`, `headline`,
   `footer-left`, `footer-right`).

3. **Render one screenshot per card**, filling the slots via
   `page.evaluate()` and waiting on `document.fonts.ready` before the
   shot. JPEG at ~88% quality lands around 50 KB for a dark card; PNG is
   better only for flat color or crisp edges.

4. **Reference it** with the full absolute URL — crawlers do not resolve
   relative `og:image` paths reliably — plus `og:image:width`, `height`,
   `type`, and a real `og:image:alt`.

## The layout that reads at thumbnail size

Previews are shown small. The constraints that matter:

- **A headline of 4–8 words**, set in the display face at ~72–76px. Anything
  longer is illegible in a chat list.
- **One accent color**, used once — an italic phrase or a single rule.
- **A kicker line** in the mono/label face, uppercase, wide tracking, to
  carry the where and the what.
- **A footer rule plus two columns** — identity on the left, status on the
  right. This is where a card earns its keep: it is the natural place for
  *spec concept*, *template preview*, *not affiliated*, or a date.
- **Generous margins** (~74px). Some surfaces crop the edges.

## The honest-card rule

Whatever the card claims is what a recipient believes before they click,
and most never click. If the page is a demo with invented figures, a spec
build for a business that has not commissioned it, or a draft — **say so
on the card**, in the footer, in the same type as everything else.

This is not a disclaimer bolted on. A card that reads "template preview ·
figures illustrative" is more persuasive than one that pretends, because
the recipient can tell immediately what they are being shown and doesn't
have to work out whether they've been misled.

Generating cards is cheap enough that this costs nothing: one line of
template data per page.

## Failure mode

If the render step is skipped, `og:image` points at a 404 and most
surfaces fall back to *no image at all* rather than showing a broken one —
so a missing card looks exactly like a page that never had one. Check the
file exists at the absolute URL before shipping; a preview cannot be
tested by looking at the page.
