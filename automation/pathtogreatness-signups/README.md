# The Path to Greatness: sign-ups and welcome email

How a sign-up on **eatmediatv.com/pathtogreatness** becomes a row in a private
Google Sheet and a welcome email from eatmediatv@gmail.com.

```
visitor types email ──▶ Apps Script web app ──▶ private Sheet "The Path to Greatness · First Readers"
   (thank-you popup)      (Google-hosted)            tab Signups, Status = new
                                                           │
                                       n8n on the Mac Studio, every 2 minutes
                                                           │
                                         Gmail (eatmediatv@gmail.com) sends the welcome email
                                         row Status = welcomed
```

Why two pieces: the Mac's n8n is not reachable from the internet (Tailscale
Funnel was dropped), so the site cannot post to it. Google hosts the part that
must never be down, the capture. If the Mac is asleep, sign-ups still land in
the sheet and get their welcome email when n8n is back.

| File | What it is |
|---|---|
| `apps-script/Code.gs` | The whole web app in one file: validates and de-duplicates sign-ups, writes the row, serves the unsubscribe page. No secrets in the file. |
| `email/welcome.html` | The welcome email (HTML). Every quoted line is verbatim from the book with its page. |
| `email/welcome.txt` | The same email as plain text, for reference. |
| `n8n/ptg-welcome-email.json` | The n8n workflow "PTG: Welcome email". Built from the email by `build_workflow.py`; do not edit by hand. |
| `n8n/build_workflow.py` | Rebuilds the workflow after the email changes. |
| `n8n/install.sh` | Installs the workflow into the Mac's n8n: backs up the database, links credentials by name, imports it switched off. |

The sheet: https://docs.google.com/spreadsheets/d/1QodevbYpJ7VLTZzdl058YS0sQ1zg99qJ-OioZRi6aDU/edit
(private to eatmediatv@gmail.com). Its "How this works" tab explains every
Status value.

## One-time setup

**A. The sign-up endpoint (about 3 minutes, in the browser, signed in as eatmediatv@gmail.com)**

1. Open the sheet, then **Extensions → Apps Script**.
2. Delete what is in `Code.gs`, paste the whole of `apps-script/Code.gs`, press **Save**.
3. In the function menu choose **setup**, press **Run**, and allow access when Google asks. The log should say "Ready".
4. **Deploy → New deployment**. Type: **Web app**. Execute as: **Me**. Who has access: **Anyone**. Press **Deploy**.
5. Copy the **Web app URL** (it ends in `/exec`).
6. In the Apps Script editor open **Project Settings** (gear icon) → **Script properties** → **Add script property**. Property `EXEC_URL`, value: the Web app URL. **Save**. Unsubscribe links in the emails are built from it. Check: open the Web app URL with `?a=health` on the end; it should say `"ok":true` and `"unsubscribe_links":"set"`.
7. Put it in `FORM_ENDPOINT` at the top of `eatmedia/pathtogreatness/assets/ptg.js` in both repos (or send it to Claude to do). Until it is set, the page falls back to opening the visitor's mail app, and the phone sign-up panel stays off.

To change the code later, paste the new version and use **Deploy → Manage deployments → edit → Version: New version**, so the URL stays the same.

**B. The welcome email (about 5 minutes, on the Mac)**

In Terminal:

```bash
cd ~/Downloads
curl -fsSLO https://raw.githubusercontent.com/Dixon8303/ImaginariumOzone/main/automation/pathtogreatness-signups/n8n/install.sh
bash install.sh
```

Then follow the four steps it prints: open "PTG: Welcome email" in n8n, check the
two credentials (the Gmail one decides the sender), run it once after a test
sign-up, and switch it on.

## Running it

- Sign-ups and their state live in the sheet. The Summary tab counts them.
- To resend a welcome email, set that row's Status to `new`.
- Unsubscribe links in the email mark the row `unsubscribed`; n8n never emails those rows.
- "Signed up from" records which button brought each address: `page form` (the form near the foot of the page), or on phones the button that raised the sign-up panel (`hero`, `menu`, `bar`, `excerpt`, `inventory`, `fieldwork`, `pledge`). Read it with the UTM columns to see which placement works.
- Kill switch: switch the n8n workflow off. Capture keeps working.
- Limits: consumer Gmail allows roughly 500 sends a day; n8n sends at most 20 every 2 minutes. The endpoint accepts at most 300 new sign-ups an hour as a flood guard.

## Spec (loop-engineering format)

```
TASK:     First-readers welcome
TRIGGER:  every 2 minutes (n8n Schedule Trigger)
INPUT:    Sheet "The Path to Greatness · First Readers", tab Signups, rows with Status = new
RULES:    send only to Status = new; never to unsubscribed; at most 20 per run
STEPS:    read new rows → mark sending → send welcome email → mark welcomed (or error + reason)
OUTPUT:   each new sign-up receives one welcome email and its row reads "welcomed" with a time
CHECK:    Summary tab: "Waiting for the welcome email" returns to 0 within 4 minutes of a sign-up
          while the workflow is on; no row stays "sending"; "Welcome email failed" stays 0
ESCALATE: content of the email, any bulk or announcement send, deleting rows, changing the sender
```

## Testing

`apps-script/Code.gs` has a local test harness (Node, Apps Script services
mocked) covering sign-up, duplicates, the honeypot and timing trap, formula
injection, the flood cap, and the unsubscribe round trip. It lives in the build
notes, not in this repo; the behaviour it checks is listed above.
