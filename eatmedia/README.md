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

## Pricing — reconciled against the original spreadsheet

The live site's own price list had drifted from what it was set up
against — most notably, its "30 Minute Model Package" (Platinum tier)
was $150 where the [source spreadsheet](https://docs.google.com/spreadsheets/d/1v71DXyfjOeUW_tCTfHQ9rim6cfT1F-aWnQtI7OkLiOs)
shows $850, the only entry that broke an otherwise consistent
30/60/90-minute price ladder in every other category. `photoshoot-packages.html`
publishes the spreadsheet's numbers as the source of truth:

- Premier Packages (premium location + makeup) — $850 / $900 / $1,000
- Studio Professional Packages (Lightbender Lab + makeup) — $450 / $500 / $600
- On-Location Pro Shoot Packages (makeup, on location) — $400 / $450 / $500
- Lightbender Lab Studio Packages (studio only) — $300 / $350 / $400
- Travel Packages — $300 / $350 / $400
- Event Photography — $75/hr, 2-hr minimum ($150)
- Organizational Headshot Packages — $75 / $50 / $40 per person, by group size
- Additional photo edit — $20 each

Two things worth double-checking against what you actually want live:

1. The live site's "On Location Shoot" category (Professional Picture /
   Premier Portrait / Platinum Prestige) was priced $250/$300/$350 —
   that triple doesn't match any category in the spreadsheet at all. The
   closest match by description (makeup artist included, on location) is
   "On-Location Pro Shoot Packages" at $400/$450/$500, which is what's
   published now. If $250/$300/$350 was an intentional, separate lower
   tier, let me know and I'll add it back as its own category.
2. The spreadsheet's **Video Production rates** (editing, on-location
   shooting, additional crew) weren't on the live site at all — they're
   now on the home page's Video Production section. Confirm those are
   still current before this goes live.
3. The site's flashy package names (Platinum, Diva, Mannequin, Vogue
   Essence, etc.) were dropped in favor of the spreadsheet's plain
   category/duration names, since the spreadsheet is the source of
   truth and doesn't define those names. Happy to reintroduce them as
   marketing labels over the correct prices if you want that back.

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

- `index.html` — the "In Production" list and video rates.
- `photoshoot-packages.html` — the price grid (see the reconciliation
  notes above before changing anything here).
- `about.html` — team/experience copy.
- Contact block (email/phone/hours) is repeated at the bottom of all
  three pages and in the footer — update in all four spots together.
