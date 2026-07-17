# Marvel Studios Release Tracker

Notifies you (native iOS push + text message) whenever Marvel Studios
announces or reschedules a movie, Disney+ series episode, short, or special
presentation, and keeps a dedicated iCloud calendar in sync — new items get
added, changed release dates move the existing event instead of duplicating
it.

Runs for free once a day via a GitHub Actions cron workflow
(`.github/workflows/marvel_tracker.yml`) — no server to maintain.

## How it works

1. `tmdb_client.py` pulls every Marvel Studios movie and show from
   [TMDb](https://www.themoviedb.org) (filtered by company id 420), including
   every episode and season-0 special of each tracked show.
2. `tracker.py` diffs that against `state.json` (committed in this repo) to
   find anything new or whose date changed.
3. `calendar_client.py` creates or updates the matching event on a dedicated
   "Marvel Releases" iCloud calendar via CalDAV.
4. `notifier.py` sends an iOS push (via [ntfy](https://ntfy.sh)) and a text
   message (via your carrier's email-to-SMS gateway) summarizing what
   changed.
5. `state.json` is updated and the workflow commits it back to the repo, so
   tomorrow's run has an accurate baseline to diff against.

Coverage caveat: TMDb has no single "everything Marvel Studios" endpoint, so
some shorts/specials may be tagged inconsistently. Use `tracked_ids.yaml` to
add anything missing or exclude false positives — worth a glance every few
months.

## One-time setup

### 1. TMDb API key (free)
Create an account at themoviedb.org → Settings → API → request a free API
key (v3 auth).

### 2. iCloud calendar + app-specific password
1. In the Calendar app (iCloud), create a new calendar named **Marvel
   Releases** (matches `ICLOUD_CALENDAR_NAME` default — change the env var if
   you name it differently).
2. Go to [appleid.apple.com](https://appleid.apple.com) → Sign-In and
   Security → App-Specific Passwords → generate one for this tracker.
   Two-factor authentication must be enabled on the Apple ID.

### 3. Push notifications (ntfy — free, no account)
1. Install the **ntfy** app from the iOS App Store.
2. Pick a private, hard-to-guess topic name (e.g.
   `marvel-tracker-yourname-a1b2c3`) and subscribe to it in the app.
   Anyone who knows the topic name can publish to it, so keep it non-obvious.

### 4. Text messages (carrier email-to-SMS gateway — free)
Find your carrier's gateway domain and set `SMS_GATEWAY_ADDRESS` to
`<your-10-digit-number>@<gateway-domain>`, e.g.:

| Carrier   | Gateway domain          |
|-----------|--------------------------|
| Verizon   | `vtext.com`              |
| AT&T      | `txt.att.net`            |
| T-Mobile  | `tmomail.net`            |

Sending is done via free Gmail SMTP: use a Gmail account and create an
[App Password](https://myaccount.google.com/apppasswords) for it (requires
2-Step Verification on that Google account).

### 5. GitHub repository secrets
Set these under Settings → Secrets and variables → Actions:

| Secret                          | Value                                   |
|----------------------------------|------------------------------------------|
| `TMDB_API_KEY`                  | TMDb API key from step 1                |
| `ICLOUD_APPLE_ID`                | Your Apple ID email                     |
| `ICLOUD_APP_SPECIFIC_PASSWORD`   | App-specific password from step 2       |
| `NTFY_TOPIC`                     | Topic name from step 3                  |
| `SMS_GATEWAY_ADDRESS`            | `number@gateway-domain` from step 4     |
| `GMAIL_ADDRESS`                  | Gmail address used to send              |
| `GMAIL_APP_PASSWORD`             | Gmail App Password from step 4          |

### 6. Test it
Trigger the workflow manually once (Actions tab → Marvel Release Tracker →
Run workflow) instead of waiting for the daily cron, and confirm:
- The run completes without errors.
- New events appear on the "Marvel Releases" calendar and sync to your
  iPhone.
- The ntfy app shows a push notification and a text arrives.
- `marvel_tracker/state.json` gets committed with the new entries.

## Local development

```bash
pip install -r marvel_tracker/requirements.txt
export TMDB_API_KEY=...
export ICLOUD_APPLE_ID=...
export ICLOUD_APP_SPECIFIC_PASSWORD=...
export NTFY_TOPIC=...            # optional locally
export SMS_GATEWAY_ADDRESS=...   # optional locally
export GMAIL_ADDRESS=...         # optional locally
export GMAIL_APP_PASSWORD=...    # optional locally

python -m marvel_tracker.tracker
```
