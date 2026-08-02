# What History Buried — official site

Pure static site for **What History Buried** (The Black Genius Files, Vol. 1),
compiled from the Claude Design prototypes in [`design-src/`](design-src/).
No build step, no backend — ready for GitHub Pages.

## Pages & anchors (the automation deep-links to these — keep stable)

| URL | Purpose |
|-----|---------|
| `/` | The official site — case files, evidence room, timeline, excerpt, `#acquire` (aliases `#buy`, `#free-chapter`), deep links `#bgf-001`…`#bgf-012` |
| `/links.html` | Link-in-bio hub: Book, Free Chapter, Archive, Genius Index, Podcast, Press Kit |
| `/press-kit.html` | One-page press kit for media & educators |
| `/free-chapter.html` | Stable redirect → `/#free-chapter` (the Recovery List capture) |
| `/privacy.html` | GA4 + email-capture disclosures |
| `/404.html` | Not-found page (picked up automatically by GitHub Pages) |

## Images

All art is real (uploaded and optimized), including `img/cover.jpg` (the
titled front cover) and `img/StudyCompanion_Thumb_Portrait.jpg` (the
Companion's promotional graphic — despite the "_1000.png" name used
earlier, the real asset is a portrait poster, not a square; it was renamed
and recompressed to JPEG to fit the mobile budget).

Both product-card images in `#acquire` share `aspect-ratio:3/4;
object-fit:cover` so they render at matching sizes regardless of each
source image's native aspect ratio — keep that pairing if either image is
swapped for a new version, so future cards line up too.

Easiest path for new/updated art: GitHub → **Add file → Upload files** into
`site/img/` on a branch, keep the filename, merge. Keep it ≤200 KB (the
traffic arrives from
Shorts and pins on mobile).

## Config

Everything configurable lives in **one config block** at the top of
[`assets/site.js`](assets/site.js):

| Key | Status |
|-----|--------|
| `PAYHIP_PRODUCT_ID` | ✅ `exquo` → https://payhip.com/b/exquo (static buy-button hrefs match, so the no-JS fallback works too) |
| `PAYHIP_STORE_URL` | ✅ https://payhip.com/BlackGeniusFiles (hub "Full Bookstore" link) |
| `PAYHIP_STUDY_URL` | ✅ https://payhip.com/b/R0jgn (Study & Trivia Companion — hub row 08, FAQ Q·05, and a product card in `#acquire`) |
| `YOUTUBE_URL` | ✅ https://www.youtube.com/@theblackgeniusfiles — same URL as the `YT.url` config in `black-genius-files`' `assets/data.js`; keep them matching if either changes |
| `AMAZON_URL` | ✅ https://a.co/d/0g29KbPj (trade paperback — the Kindle ebook link is intentionally unused) |
| `GA4_MEASUREMENT_ID` | ✅ `G-FXDJLKSKDG` |
| `FORM_ACTION` | ✅ Kit form `9748584` (posts `email_address`; the incentive email delivers the Chapter 1 PDF) |
| `PODCAST_URL` | ✅ The All Black Everything Podcast (Apple Podcasts) |
| `PINTEREST_URL` | ⬜ Remaining links.html hub destination |
| `CONTACT_EMAIL` | ✅ eatmediatv@gmail.com |

Buy buttons, GA4, the email form, and hub links are all wired from that block at
page load. GA4 and the form stay safely disabled until their values look real.

If the Payhip product ID ever changes, update the config block **and**
search-and-replace `payhip.com/b/exquo` across the HTML so the no-JS fallback
hrefs stay in sync. Also replace `ISBN_PLACEHOLDER` in `index.html`'s JSON-LD
once the ISBN is assigned.

## Tracking

- GA4 loads from the config block (`MEASUREMENT_ID`).
- Inbound UTM params (`utm_source=youtube|pinterest`, `utm_campaign=bgf_engine`,
  `utm_content=<id>`, …) are captured on landing, kept in `sessionStorage` for
  the visit, and appended to every outbound Payhip / Amazon link — attribution
  survives internal navigation and the click out to checkout.

## Deploy — LIVE at the repo URL

This site is deployed by this repo's Pages workflow
([`.github/workflows/pages.yml`](../.github/workflows/pages.yml)), which
publishes the assessment (`docs/`) at the root and this folder under `/book/`
on every push to `main`:

**https://dixon8303.github.io/ImaginariumOzone/book/**

All internal paths are relative, so the site works at any mount point. The
`CNAME` file is deliberately excluded from the deploy for now, and all
canonical/OG/sitemap URLs point at the repo URL above.

### Later: going live on blackgeniusfiles.com

When the domain is ready:

1. Add DNS records at the registrar:

   | Type | Host | Value |
   |------|------|-------|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `dixon8303.github.io` |

2. Move this site to its own Pages site (a dedicated repo, e.g.
   `blackgeniusfiles`, with these files at the root — the custom domain
   applies to a whole Pages site, and this repo's root already serves the
   assessment). Keep `.nojekyll` and `CNAME` (it contains
   `blackgeniusfiles.com`; Pages reads it automatically).
3. Point the URLs back at the domain:
   `grep -rl 'dixon8303.github.io/ImaginariumOzone/book' . | xargs sed -i 's|https://dixon8303.github.io/ImaginariumOzone/book/|https://blackgeniusfiles.com/|g; s|/ImaginariumOzone/book/|/|g'`
4. **Enforce HTTPS** in Pages settings once the certificate is issued
   (DNS + cert can take up to 24 h the first time).

Note: while served under `/book/`, `robots.txt` and `sitemap.xml` are inert
(crawlers only read them from a domain root) — they activate once the site
moves to its own domain.

## Performance

Built mobile-first for traffic arriving from Shorts and pins: no frameworks, no
iframes, system fonts only, one WebP cover (~18 KB) and one OG JPEG (~90 KB).
The only third-party scripts are Payhip's overlay and (once enabled) GA4 —
both deferred. Target: Lighthouse mobile ≥ 90.
