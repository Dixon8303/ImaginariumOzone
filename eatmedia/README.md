# E.A.T. Media — company site

Static site for **Everything, All That Media LLC** (E.A.T. Media), a video
production and photography studio — "Capture Your Vision." No build step,
no backend — ready for GitHub Pages, same pattern as
[`site/`](../site/README.md).

## What's here

Three pages, rebuilt from the real content on the current live site
(`everythingallthatmediallc.godaddysites.com`, exported and supplied
directly) and the original pricing spreadsheet, refreshed and
restructured but not reinvented:

- **`index.html`** (Home) — hero with the real Vimeo background video
  (`75851958`) the live site uses, phone/hours, the mission statement, the
  current "In Production" slate (podcasts + the Godfood documentary),
  video production rates, a photography summary, and the full five-area
  Photoshoot & Media Readiness Prep guide (copy-credited to Emily London
  Portraits, per the source).
- **`about.html`** — Our Vision, Our Team, Our Experience, and social
  links, matching the live About page.
- **`photoshoot-packages.html`** — the full photography price menu.
- **`assets/style.css`** / **`assets/site.js`** — shared styling (real
  brand font pair, Archivo Black + Montserrat, and real brand blue
  `#0292eb`) and the one bit of shared JS (footer year).
- **`assets/manifest.webmanifest`** — same web-app manifest as the live
  site (name, icons, theme color).

Real assets are hotlinked from the live site's own CDN
(`img1.wsimg.com`) — the logo, the favicon, and every photo — rather than
invented placeholders. **Before ever canceling the GoDaddy Website
Builder subscription**, download and self-host these images under
`eatmedia/img/` (same pattern as `site/img/`), since canceling that
account will likely take the CDN URLs down with it.

## Pricing — the 2026 rate card (customer-facing only)

`photoshoot-packages.html` (nav label "Pricing") now publishes the
[2026 rate card](https://docs.google.com/spreadsheets/d/1Tp1NcX9rHCS_wWYi1IZQkOOfltMMY7sICEpG1WWExk8) —
this superseded an earlier, now-retired reconciliation against a prior
pricing spreadsheet. Published sections: Photography Session Packages
(Studio Session / Studio Pro / On-Location Session / On-Location Pro /
Premier Experience, each at 30/60/90 min), Event Coverage, Organizational
Headshot Day, Video Production (shooting), Video Post-Production
(editing tiers), Additional Crew, Content Retainers, Specialty (podcast /
livestream / drone), Add-Ons & Licensing, and Booking & Payment Terms.

**Deliberately left off the site**, because the source sheet marks it
internal-only (rate-engine multipliers, market calibration, per-line
margin/contribution-dollar math, LA permit/operating cost notes, and the
old-vs-new pricing changelog) or because it's explicitly "not a published
menu" in the sheet itself: the Community/Independent Artist track's
eligibility rules, capacity cap, and multiplier. The site keeps only a
soft, mechanics-free footnote on the Pricing page ("available by
application — reach out to ask"), since the sheet's own public-facing
banner text says that much should be visible.

The old "$50 refundable deposit" language is gone everywhere it appeared
(home page and pricing page) — booking terms are now: free 20-minute
discovery call, a $75 hold for a 60-minute strategy session (credited to
the booking), and a 50% non-refundable retainer to confirm the date.

**Lightbender Lab is gone.** Every named reference to it — in the rate
card banner, the Studio Session/Studio Pro package descriptions, and an
About-page photo caption that called it "E.A.T. Media's exclusive studio
location" — has been removed. Studio Session and Studio Pro now describe
the in-house setup (background stands, white and black seamless
backdrops) instead of naming a studio. When a shoot actually needs a
dedicated studio space, that's now a pass-through "studio rental" fee
(Add-Ons & Licensing, and a footnote under the package cards) — at cost,
same pattern as permits/venue/parking. No studio is named on the site.

## Staging — LIVE at the repo URL

Deployed by this repo's Pages workflow
([`.github/workflows/pages.yml`](../.github/workflows/pages.yml)), mounted
under `/eatmedia/` alongside the assessment (`docs/`, at the root) and the
book site (`site/`, at `/book/`):

**https://dixon8303.github.io/ImaginariumOzone/eatmedia/**

The `CNAME` file is deliberately excluded from that deploy for now (a custom
domain applies to a whole Pages site, not a subfolder) — see below.

## Going live on eatmediatv.com

`eatmediatv.com` currently points at a GoDaddy Website Builder site
(`everythingallthatmediallc.godaddysites.com`). To replace it with this site:

1. **Self-host the hotlinked images** under `eatmedia/img/` (see above),
   and update the `src` attributes across the three pages.
2. **Move this folder to its own Pages site** — a dedicated repo (e.g.
   `eat-media`), with these files at the root. Keep `CNAME` (it contains
   `eatmediatv.com`; Pages reads it automatically).
3. **Update DNS at the registrar** (GoDaddy, since that's where the domain
   is registered) — replace whatever records currently point the domain at
   Website Builder with:

   | Type | Host | Value |
   |------|------|-------|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `<your-github-username>.github.io` |

4. In the new repo's **Settings → Pages**, set the custom domain to
   `eatmediatv.com` and **enable HTTPS** once the certificate issues (DNS +
   cert can take up to 24h the first time).
5. Optionally cancel/downgrade the GoDaddy Website Builder subscription for
   this site once the cutover is confirmed working — not before, and not
   until step 1 is done, so there's no gap where images or the domain
   itself go dark.

Until that cutover happens, this page is safe to iterate on at the staging
URL above with zero risk to the live GoDaddy site.

## Positioning — media venture studio, not just production-for-hire

The site now frames E.A.T. Media as the studio behind an independent
media catalog (Black Genius Files, What History Buried, The Genius
Index, Dixon Grant Studio), not only a production shop for hire —
that's the real, honest differentiator available here without inventing
case studies, testimonials, or client logos that don't exist. Concretely:

- Hero eyebrow + subhead reframe the offer ("A Los Angeles Media Venture
  Studio... the studio behind an independent book, documentary, and
  podcast catalog"), keeping the real "Capture Your Vision" tagline.
- A new **"Beyond Production"** section on the home page (`#studio`)
  cross-links all four ecosystem properties plus the full Link Console.
- The same five links repeat in the footer of all three pages, under
  "More From E.A.T. Media" — so every ecosystem link gets at least two
  points of exposure site-wide.
- `about.html` adds one bridging line pointing back to the catalog.
- The JSON-LD `sameAs` array on the home page now includes the real
  ecosystem URLs alongside the social profiles.

**On the bigger ask** ("run a full 12-phase agency rebuild — Pentagram,
IDEO, McKinsey, Awwwards-tier, score every page 9.5+, don't stop until
diminishing returns"): I did the highest-leverage, honest part of that —
real strategic repositioning and cross-linking, grounded in what
actually exists. I didn't do the rest, on purpose: competitor teardown
research, a from-scratch bespoke component/motion-design system, and
"trust engineering" (case studies, testimonials, client logos, awards,
stats) either need real inputs I don't have (your competitors, your
brand assets, actual client outcomes) or would mean fabricating content
on a real business's public site to hit a design-agency checklist. If
you want to go further, the useful next inputs are: real client
testimonials/case studies, any analytics you have on the current site,
and named competitors you want positioned against — with those, the
next round can go much further for real instead of performing it.

## What didn't carry over

- **The contact form.** The live site's "Send Message" form posts to
  GoDaddy's own hosted form backend (with reCAPTCHA) — that doesn't
  exist for a static site. For now, Contact sections use direct
  `mailto:`/`tel:` links instead of a fake form. Wire up a real form
  backend (Formspree, Netlify Forms, etc.) if you want an inline form
  back.
- **The About page's Instagram feed and Reviews widgets** — both were
  GoDaddy-hosted embeds pulling live/dynamic content. `about.html` links
  out to the real Instagram profile instead of faking a feed, and drops
  the Reviews section rather than inventing testimonials — add real
  ones whenever you have them to publish.

## Editing

- `index.html` — the "In Production" list, video rates, and the "Beyond
  Production" (`#studio`) ecosystem cards.
- `photoshoot-packages.html` — the full rate card (see the pricing notes
  above before changing anything here).
- `about.html` — team/experience copy.
- Contact block (email/phone/hours) is repeated at the bottom of all
  three pages and in the footer — update in all four spots together.
- The "More From E.A.T. Media" footer links are duplicated across all
  three pages' footers — update all three together if a URL changes.
