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

## Technical, UX, and accessibility pass

A further round against the original 12-phase agency brief — the parts
of it that were honestly deliverable with the tools and real content
available, verified rather than just asserted:

- **Market position (real, lightweight).** Checked the rate card against
  actual 2026 LA market data — headshots run $400-1,200+, small-business
  video $1,200-8,200. This card sits appropriately in-market; no pricing
  changed as a result, this was a sanity check, not a rewrite.
- **Mobile navigation.** The 5-item nav wrapped awkwardly on narrow
  screens; it now collapses into a proper hamburger toggle
  (`assets/site.js` + `.nav-toggle` in `assets/style.css`), no dependencies.
- **Scroll-reveal.** Sections fade/lift in on scroll via
  `IntersectionObserver`, fully skipped under `prefers-reduced-motion`,
  and content is never hidden if JS fails (default state is visible).
  Verified with real incremental scrolling, not just a static screenshot
  — a `fullPage` Playwright screenshot taken without scrolling first is
  a false positive/negative for this pattern, worth remembering if you
  test it again.
- **Sticky mobile CTA.** A fixed Call / Get a Quote bar on screens
  ≤720px, since the primary conversion actions were easy to miss once
  scrolled past the hero.
- **FAQ (honest trust-building, not fabricated).** New FAQ section on
  the Pricing page, plus `FAQPage` structured data — six questions, and
  every answer is a restatement of a policy that already exists
  elsewhere on the page. Nothing invented.
- **Open Graph images.** All three pages were missing `og:image` /
  `twitter:image` entirely (no share-card image at all); now set from
  real photos already used on each page, with `twitter:card` upgraded to
  `summary_large_image`.
- **Accessibility.** Added a skip-to-content link on all three pages.
  Ran real WCAG contrast math (not eyeballed) on every text/background
  pairing: the brand blue `#0292eb` is only 3.1-3.3:1 against the
  site's light backgrounds — fine for large UI (buttons, borders, price
  numerals) which only need 3:1, but body-size links and small labels
  need 4.5:1 and were failing. Added a `--link` token (`#0275bc` in
  light mode, same as `--accent` in dark mode where it already passes)
  used for regular links, the eyebrow labels, and the small rate-price
  figures — the brand blue itself is untouched everywhere it was already
  compliant (buttons, badges, large price display).
- `robots.txt` / `sitemap.xml` added, matching `site/`'s pattern (inert
  until the folder is served from a domain root — see below).

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

## Honest scorecard against the 12-phase brief

Asked to keep working through the original 12-phase agency brief and
self-score against it. Real assessment, not inflated to hit a number:

| Phase | Status | Why |
|---|---|---|
| 1. Strategic audit | Done | Real diagnosis: production-for-hire framing wasted the owned-catalog differentiator. |
| 2. Market position | Done (lightweight) | Checked real 2026 LA pricing data — the rate card is market-appropriate. No named-competitor teardown; wasn't asked for and risks inaccurate claims about businesses I can't verify in depth. |
| 3. Narrative | Done | Hero, About, and site-wide framing rewritten around the venture-studio positioning. |
| 4. Information architecture | Done | Nav simplified to what's real; mobile nav fixed; jump-nav added to the long pricing page. |
| 5. Visual system | Partial | One coherent, documented system (type/color/spacing/components) — real brand assets (font pair, blue, logo), not a from-scratch bespoke system built without design input. |
| 6. Experience design | Partial | Mobile nav, scroll-reveal, sticky CTA, FAQ accordion, focus states all real and verified. No custom video/photo interactions (lightbox, filtering) — not clearly needed yet. |
| 7. Trust engineering | Capped, honestly | FAQ is real. Case studies/testimonials/awards/client logos are **not fabricated** — this phase cannot score highly without real assets from you. |
| 8. Conversion optimization | Done | Sticky mobile CTA, consistent primary-action hierarchy, low-friction discovery-call framing repeated at the top of Pricing. |
| 9. Technical excellence | Done | og:image added (was missing entirely), sitemap/robots added, real WCAG contrast math run and fixed (not eyeballed), skip link, valid structured data. |
| 10. Brand expansion | Done | Ecosystem cross-linking (this round + the positioning round). |
| 11. Luxury pass | Partial | Real, verified detail work (contrast, motion, nav) over a system built from real brand assets — not a claim of Apple/Stripe-tier bespoke design, which needs a design process this can't simulate. |
| 12. Continuous improvement | This table | Every "Partial"/"Capped" row above is capped by a real constraint (no design partner, no client assets to fabricate from) — not by remaining effort. More rounds won't move those without new real inputs. |

If you want to push further: real client testimonials/case studies, any
analytics from the current site, and named competitors you want
positioned against would unlock Phases 2, 7, and 11 for real instead of
performing them.

## Verified audit round (6 independent lenses + a skeptical verifier)

Ran a structured audit — six reviewers (customer UX/conversion,
information architecture, accessibility, technical/SEO/performance,
content accuracy/cross-page consistency, CSS design-system quality) each
independently read the real source files, followed by a verifier that
re-checked every finding against the actual code before anything was
acted on. 24 of 36 raw findings were confirmed real and fixed, including:

- A real CSS bug: Content Retainer prices ($1,875–$5,625/mo) were
  silently rendering as unstyled plain text — the `.tier-price` styling
  rule only matched `.price-card`, but the retainer cards use
  `.package-card`. Fixed with a proper rule instead of the inline
  `font-size` hack that was masking it.
- The homepage's "See Our Work" hero button linked to the ecosystem
  cross-link section, not the actual "From the Studio" photo gallery —
  fixed.
- A genuine self-contradiction on the About page: "over 10 years in the
  industry" next to the site's own "est. 2020." Reworded to attribute
  the 10 years to the team's prior experience, distinct from the
  company's founding date, rather than guessing at a number.
- The sticky header (with no `scroll-margin-top` anywhere) was hiding
  the top of every anchor-jump target site-wide — fixed with one rule.
- Two more spots using the raw brand blue for sub-large text/badges
  (missed in the earlier contrast pass) — switched to `--link`.
- `http://bit.ly/abepodcast` (the only plain-http link on the site),
  `Llc` → `LLC` casing in social-preview meta tags, missing
  `aria-current`/`h1`/`twitter:site`/`defer` inconsistencies across
  pages, dead CSS (`.mission`, `.price-group`, an unused `.pkg-best`),
  a non-responsive 3-column price grid cramped on phones, canonical/og
  URLs pointing at `eatmediatv.com` before that domain is actually live
  (now matches `robots.txt`/`sitemap.xml` and the same staging-URL
  convention `site/` already uses), an invalid `schema.org` value,
  a missing social-media row on the Pricing page, and a FAQ answer that
  omitted the 7-day/100%-fee cancellation clause stated elsewhere on the
  same page.

**Service area — resolved.** The Zone 1–4 travel-surcharge system is now
disclosed as based in South Los Angeles (90062) — stated on the Pricing
page banner and in the home page's JSON-LD (`address`/`areaServed`),
supplied directly by the business owner rather than guessed at.

**Still open:** the "From the Studio" gallery's photos still have
generic, numbered alt text — real captions need someone who can
actually see what's in each photo, which wasn't possible in the
environment that built this (the source Flickr images couldn't be
loaded/viewed here).

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
