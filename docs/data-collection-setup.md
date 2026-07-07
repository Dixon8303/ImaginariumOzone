# Collecting anonymized results (validation study)

You need **≥150 completed assessments** to validate the scoring system. This sets up
automatic, anonymized collection into a **Google Sheet you own** — free, no submission
cap, no third-party service. Every completed assessment becomes one row.

**What's collected:** the nine domain scores (A/B/C and composite), the resolved braid,
flags, timing, forced-rank picks, and the raw answers — as JSON. **No name, email, IP,
or account.** Takers see a checked-by-default consent line on the first screen and can
opt out; opting out keeps everything on their device and sends nothing.

---

## One-time setup (~10 minutes)

### 1. Make the sheet
1. Go to <https://sheets.google.com> and create a blank spreadsheet. Name it e.g.
   *Genius Index — Results*.
2. Copy its **ID** from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_LONG_ID`**`/edit`

### 2. Add the collector script
1. In that sheet: **Extensions → Apps Script**.
2. Delete the placeholder code, then paste the contents of
   [`apps-script/Code.gs`](./apps-script/Code.gs).
3. Near the top, set `var SHEET_ID = 'THIS_LONG_ID';` to the ID you copied.
4. Click **Save** (disk icon).

### 3. Deploy it as a web app
1. **Deploy → New deployment**.
2. Gear icon → **Web app**.
3. Set **Execute as: Me**, **Who has access: Anyone**. (This lets the public
   assessment page POST results in; it does *not* let anyone read your sheet.)
4. **Deploy**, authorize when prompted (it's your own script), and **copy the Web-app URL**
   — it looks like `https://script.google.com/macros/s/AKfy…/exec`.

### 4. Point the site at it
1. Open [`index.html`](./index.html), find near the top:
   ```js
   const SUBMIT_URL = "";
   ```
2. Paste your Web-app URL between the quotes:
   ```js
   const SUBMIT_URL = "https://script.google.com/macros/s/AKfy…/exec";
   ```
3. Commit and let the site redeploy (GitHub Pages picks it up automatically).

That's it. From now on, each completed assessment (with consent left on) appends a row.

> **Test it:** open the live site, complete a run, and watch a row appear in the sheet.
> If the network call fails, the taker still sees their full chart and a copyable data
> block they can send you manually — no data is lost.

---

## Tracking toward 150

- Put `=COUNTA(A:A)-1` in any empty cell to show your live count (minus the header row).
- Useful validation columns are already broken out per row, so you can check without
  parsing JSON:
  - **A-vs-station convergence** per domain (are self-report `A` and performance `B`
    correlated?) — the `raw_json` column holds `domains.<ID>.A` and `.B`.
  - **SDR flag rate** (`flag_sdr` column) — high rates mean the honesty items are firing.
  - **Test length** (`minutes` column) distribution — spot rushed sessions.
  - **Braid distribution** (`braid` column) — are all 36 reachable, or does scoring
    collapse everyone into a few?
  - **Forced-rank convergence** (`rank_overlap`, 0–3) — do people's self-ranking and the
    computed leaders agree?

---

## Fallback / alternatives

- **Manual copy** — always available. The results screen has a *Pilot data* section with
  a copy button; a taker can paste that JSON into an email if the endpoint is ever down.
- **Netlify Forms** — only if you also host on Netlify. Zero script, but the free tier
  caps at **100 submissions/month**, so it can't carry a 150+ study by itself. Apps Script
  above has no such cap.
