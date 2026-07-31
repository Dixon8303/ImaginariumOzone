# blackgeniusfiles.com — What History Buried site

Pure static site for **What History Buried** (The Black Genius Files, Vol. 1).
No build step, no backend — ready for GitHub Pages.

## Pages & anchors (the automation deep-links to these — keep stable)

| URL | Purpose |
|-----|---------|
| `/` | Book landing — hero, praise, chapters preview, `#free-chapter`, `#buy` |
| `/links.html` | Link-in-bio hub: Book, Amazon, YouTube, Pinterest, Podcast, Contact |
| `/free-chapter.html` | Email capture → free Chapter 1 PDF (Vol. 2 launch list) |
| `/privacy.html` | GA4 + email-capture disclosures |
| `/404.html` | Not-found page (picked up automatically by GitHub Pages) |

## One-time setup: swap the placeholders

Everything configurable lives in **one config block** at the top of
[`assets/site.js`](assets/site.js):

| Key | Where to get it |
|-----|-----------------|
| `PAYHIP_PRODUCT_ID` | Create the ebook product on payhip.com — the ID is the part after `/b/` in the product URL |
| `AMAZON_URL` | The paperback's Amazon listing URL |
| `GA4_MEASUREMENT_ID` | Google Analytics → Admin → Data streams → `G-XXXXXXXXXX` |
| `FORM_ACTION` | Beehiiv / MailerLite (free tier) form endpoint that delivers the free-chapter PDF |
| `YOUTUBE_URL` / `PINTEREST_URL` / `PODCAST_URL` / `CONTACT_EMAIL` | The links.html hub destinations |

Buy buttons, GA4, the email form, and hub links are all wired from that block at
page load. GA4 and the form stay safely disabled until their values look real.

**No-JS fallback:** the buy buttons' static `href` contains the literal
`PRODUCT_ID` placeholder. After Payhip setup, also run a one-shot
search-and-replace so no-JS visitors land on the right product page:

```bash
grep -rl 'payhip.com/b/PRODUCT_ID' . | xargs sed -i 's|payhip.com/b/PRODUCT_ID|payhip.com/b/YOUR_REAL_ID|g'
```

Also replace `ISBN_PLACEHOLDER` in `index.html`'s JSON-LD once the ISBN is assigned.

## Tracking

- GA4 loads from the config block (`MEASUREMENT_ID`).
- Inbound UTM params (`utm_source=youtube|pinterest`, `utm_campaign=bgf_engine`,
  `utm_content=<id>`, …) are captured on landing, kept in `sessionStorage` for
  the visit, and appended to every outbound Payhip / Amazon link — attribution
  survives internal navigation and the click out to checkout.

## Deploy (GitHub Pages + custom domain)

This folder is self-contained — deploy **its contents** as the root of a
GitHub Pages site (easiest: a dedicated repo, e.g. `blackgeniusfiles`, since
the custom domain applies to the whole Pages site):

1. Copy the contents of `site/` to the new repo's root (keep `.nojekyll` and `CNAME`).
2. Repo **Settings → Pages → Deploy from a branch** → `main`, folder `/ (root)`.
3. **Enforce HTTPS** in the same Pages settings once the certificate is issued.

### DNS (at your domain registrar)

| Type | Host | Value |
|------|------|-------|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `<username>.github.io` |

The `CNAME` file in this folder already contains `blackgeniusfiles.com`;
GitHub Pages reads it automatically. DNS + certificate issuance can take up to
24 h the first time.

## Performance

Built mobile-first for traffic arriving from Shorts and pins: no frameworks, no
iframes, system fonts only, one WebP cover (~18 KB) and one OG JPEG (~90 KB).
The only third-party scripts are Payhip's overlay and (once enabled) GA4 —
both deferred. Target: Lighthouse mobile ≥ 90.
