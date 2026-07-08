# The Genius Index — digital assessment

A single self-contained web page: an 81-item inventory, nine short performance
stations, a forced ranking, and a **reader-facing results chart** drawn straight from
the book *Braid Constellations* — a personalized braid card, constellation wheel,
Complete Index Grid, and Field Guide of all thirty-six braids.

Everything runs in the browser. Nothing is installed, and a taker's answers stay on
their device unless they consent to contribute anonymized results to the validation
study (see below).

- **The page:** [`index.html`](./index.html) — open it locally in any browser, or host it.
- **Public URL (once Pages is on):** `https://dixon8303.github.io/ImaginariumOzone/`

## Publishing it for free (GitHub Pages)

The included workflow ([`.github/workflows/pages.yml`](../.github/workflows/pages.yml))
publishes this `docs/` folder automatically. To turn it on, once:

1. Merge this branch to `main`.
2. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. The workflow runs on the next push to `main` (or trigger it under the **Actions** tab
   → *Deploy assessment to GitHub Pages* → **Run workflow**). Your public URL appears in
   the run summary.

No account, build step, or payment is needed by you or by anyone taking it.

> Alternative with **no workflow**: Settings → Pages → *Deploy from a branch* → branch
> `main`, folder `/docs`. Either way the site is served from this folder.

## Collecting results for validation (≥150 datasets)

By default the page collects nothing (`SUBMIT_URL` is empty). To gather anonymized
results into a Google Sheet you own, follow
[`data-collection-setup.md`](./data-collection-setup.md) — about ten minutes, one time.

## Editing

The whole instrument — questions, scoring, the 36-braid model, and the results chart —
lives in `index.html`. The braid data model is the `BRAIDS` array; results rendering is
`results()` plus `buildWheel` / `buildGrid` / `buildFieldGuide`.
