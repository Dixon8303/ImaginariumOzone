# E.A.T. Media — company site

Pure static homepage for **Everything All That Media, LLC** (E.A.T. Media),
D. Antione Dixon's publishing/production house. No build step, no backend —
ready for GitHub Pages, same pattern as [`site/`](../site/README.md).

## What's here

One page ([`index.html`](index.html)): hero, the three live ventures (The
Black Genius Files, The Genius Index, Dixon Grant Studio), the book shelf,
a founder bio, and contact. All outbound links point at real, already-live
pages in this repo or its ecosystem — nothing here is a placeholder link.

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

1. **Move this folder to its own Pages site** — a dedicated repo (e.g.
   `eat-media`), with these files at the root. Keep `CNAME` (it contains
   `eatmediatv.com`; Pages reads it automatically).
2. **Update DNS at the registrar** (GoDaddy, since that's where the domain
   is registered) — replace whatever records currently point the domain at
   Website Builder with:

   | Type | Host | Value |
   |------|------|-------|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `<your-github-username>.github.io` |

3. In the new repo's **Settings → Pages**, set the custom domain to
   `eatmediatv.com` and **enable HTTPS** once the certificate issues (DNS +
   cert can take up to 24h the first time).
4. Optionally cancel/downgrade the GoDaddy Website Builder subscription for
   this site once the cutover is confirmed working — don't touch it before
   the new site is verified live, so there's no gap where the domain
   resolves to nothing.

Until that cutover happens, this page is safe to iterate on at the staging
URL above with zero risk to the live GoDaddy site.

## Editing

Everything is inline in `index.html` — no separate config file. The three
venture cards, the shelf list, and the contact email are the sections most
likely to need updates as new books/ventures ship.
