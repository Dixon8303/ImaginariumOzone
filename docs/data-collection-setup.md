# Collecting anonymized results (validation study)

You need **≥150 completed assessments** to validate the scoring system. This sets up
automatic, anonymized collection into a **Google Sheet you own** — free, no submission
cap, no third-party service. Every completed assessment becomes one row.

**What's collected:** the nine domain scores (A/B/C and composite), the resolved braid,
shape, flags, timing, forced-rank picks, and the raw answers — as JSON. **No name,
email, IP, or account.** Starting the assessment implies consent to this (stated on the
first screen); nothing is uploaded before that.

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

That's it. From now on, every started and every completed assessment appends a row.

> **Test it:** open the live site, complete a run, and watch a row appear in the sheet.
> If the network call fails, the taker still sees their full chart and a copyable data
> block they can send you manually — no data is lost.

---

## Updating an existing deployment

If you already set this up once and `Code.gs` changes later (like this update — it added
funnel tracking and the public stats endpoint below):

1. Open your script (**Extensions → Apps Script** from the Sheet, or script.google.com).
2. Select all, delete, and paste in the new [`apps-script/Code.gs`](./apps-script/Code.gs).
   Your `SHEET_ID` is near the top — copy your existing value over before saving if you
   pasted the placeholder.
3. **Deploy → Manage deployments** → pencil icon on your existing deployment → **Version:
   New version** → **Deploy**.

The Web-app URL stays the same, so **`SUBMIT_URL` in `index.html` does not change** —
this is a script-only update. Editing `Code.gs` without redeploying a new version has no
effect on the live endpoint; the "New version" step is what actually publishes it.

Already-collected rows are never reordered or renamed — new fields are always added as
new columns at the end, so nothing you've collected so far shifts or breaks.

---

## Tracking toward 150

- Put `=COUNTA(A:A)-1` in any empty cell to show your live count (minus the header row) —
  note this now includes **start** rows too; filter the `event` column to `complete` for
  a true completions count (or just use the public stats page below, which does this for you).
- Useful validation columns are already broken out per row, so you can check without
  parsing JSON:
  - **A-vs-station convergence** per domain (are self-report `A` and performance `B`
    correlated?) — the `raw_json` column holds `domains.<ID>.A` and `.B`.
  - **SDR flag rate** (`flag_sdr` column) — high rates mean the honesty items are firing.
  - **Test length** (`minutes` column) distribution — spot rushed sessions.
  - **Braid distribution** (`braid` column) — are all 36 reachable, or does scoring
    collapse everyone into a few?
  - **Shape distribution** (`shape` column) — Tower/Ridge/Anchored/Plateau spread.
  - **Unclaimed-genius rate** (`flag_unclaimed` / `top_unclaimed` columns) — how often the
    Index surfaces a real B-over-A gap, and which domain most often carries it.
  - **Forced-rank convergence** (`rank_overlap`, 0–3) — do people's self-ranking and the
    computed leaders agree?
  - `flag_latent` and `flag_diverge` are retired columns from an earlier scoring model —
    they stay blank going forward; ignore them.

## Funnel & live stats

Every time someone clicks **Begin Part 1**, a lightweight anonymous **start** ping is
sent (timestamp + participant code only — no answers yet). Every completed run still
sends the full **complete** row as before. This lets you see drop-off, not just finishes.

The site also has a public **Live stats** page (linked from the intro screen, or
`your-site-url/#stats`) showing aggregate-only numbers — total completions, start→finish
conversion, average completion time, most common braids, and shape distribution. It reads
from the same Apps Script endpoint via `GET ?stats=1`, which returns **counts only**:
never a raw row, a participant code, or anything traceable to one person. No setup needed
beyond the redeploy above — it works automatically once your `Code.gs` is updated.

> Conversion is only meaningful from the point this feature was deployed — completions
> collected before it existed have no matching start row, so the site's very first
> "Start → finish" percentage will look low until enough post-update data accumulates.

---

## Troubleshooting

**"Syntax error: Invalid or unexpected token" (often on the `SHEET_ID` line) when you Save or Deploy.**
This almost always means the quotes around your Sheet ID became *curly* quotes
(`'` `'`) during copy-paste, or the whole spreadsheet URL got pasted in place of the ID.
Fix it inside the Apps Script editor (which never auto-curls quotes):

1. Delete the whole `var SHEET_ID = '...';` line and **retype** it by hand.
2. Use **straight** single quotes `'` and put **only the ID** between them — the segment
   between `/d/` and `/edit` in the sheet URL, e.g.
   `https://docs.google.com/spreadsheets/d/`**`1AbC…XyZ`**`/edit`.
3. Save, then Deploy again.

The committed `Code.gs` is plain ASCII, so if you paste it fresh and edit only the ID
line as above, it will compile.

## Fallback / alternatives

- **Manual copy** — always available. The results screen has a *Pilot data* section with
  a copy button; a taker can paste that JSON into an email if the endpoint is ever down.
- **Netlify Forms** — only if you also host on Netlify. Zero script, but the free tier
  caps at **100 submissions/month**, so it can't carry a 150+ study by itself. Apps Script
  above has no such cap.
