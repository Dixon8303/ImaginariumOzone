# HoneyDrip Daily Brief Setup

Automated daily email reports of your trading activity: positions, P&L, signals, and performance metrics.

## One-Time Setup

### 1. Add GitHub Secrets for Alpaca and Email

On GitHub.com, go to **Settings → Secrets and Variables → Actions** and create these secrets:

**Trading credentials:**
```
APCA_API_KEY_ID = <your_paper_key_id>
APCA_API_SECRET_KEY = <your_paper_secret>
```

**Email delivery:**
```
GMAIL_ADDRESS = eatmediaTV@gmail.com
GMAIL_APP_PASSWORD = <16-char app password from Google Account>
EMAIL_RECIPIENT = eatmediaTV@gmail.com
```

#### Getting Gmail App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select **Mail** and **Windows Computer** (doesn't matter)
3. Google generates a 16-character password
4. Copy it to GitHub as `GMAIL_APP_PASSWORD` secret
5. Keep it safe — treat it like your Gmail password

#### Why not your regular Gmail password?

App passwords are safer: they only work for this one app, can't access your Google account, and can be revoked instantly without changing your main password.

**Never commit these secrets to the repository.**

## What You Get Daily

```
Account Status
├─ Current equity & P&L
├─ Cash available / buying power
└─ Day's P&L summary

Open Positions
├─ Symbol, quantity, entry price
├─ Current price & unrealized P&L
└─ % gain/loss per position

Today's Signals & Trades
├─ Timestamp of each trade
├─ Action (BUY/SELL) & qty
├─ Signal source (RS-02, H-25, etc.)
└─ Execution mode (paper/live)

7-Day Summary
└─ Trade count per day for past week
```

## How It Works

**Daily at 08:00 UTC (Mon–Fri):**
1. ✓ GitHub Actions runs the workflow
2. ✓ Fetches your Alpaca account data (equity, positions, P&L)
3. ✓ Reads today's trade log
4. ✓ Generates formatted brief
5. ✓ Commits it to `honeydrip_bot/briefs/<YYYYMMDD>.txt` (git history)
6. ✓ Sends it to your email via Gmail SMTP

**What you receive:**
- Account equity and cash balance
- Current open positions with unrealized P&L
- All trades executed today with timestamps
- 7-day trade summary

## Manual Brief Generation

To generate a brief on-demand:

```bash
export APCA_API_KEY_ID=<your_paper_key>
export APCA_API_SECRET_KEY=<your_paper_secret>
export HONEYDRIP_ARMED=YES

python -m honeydrip_bot.daily_brief
```

Briefs are automatically saved to `honeydrip_bot/briefs/` for long-term tracking in git history.

## Workflow Schedule

- **Trigger:** Monday–Friday at 08:00 UTC (3 AM ET / midnight PT)
- **Frequency:** Once per trading day, before market open
- **Output:** Brief saved to `honeydrip_bot/briefs/<YYYYMMDD>.txt` and committed to main
- **Artifacts:** GitHub Actions stores 30 days of brief artifacts

## Disabling or Customizing

### Skip a day's brief
The workflow only triggers Mon-Fri. To run manually:

```
GitHub Actions → "HoneyDrip Daily Brief" → "Run workflow" → select branch → Run
```

### Change the daily time
Edit `.github/workflows/honeydrip_daily_brief.yml`:

```yaml
on:
  schedule:
    - cron: '30 10 * * 1-5'  # New time: 10:30 UTC
```

Cron times are in UTC. Use [crontab.guru](https://crontab.guru) to convert your timezone.

### Add more metrics
Edit `honeydrip_bot/daily_brief.py` to add new fields to the brief output (volatility, Sharpe ratio, etc.).

## Troubleshooting

**Workflow fails with "auth error":**
- ✓ Verify `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` are set in GitHub Secrets
- ✓ Ensure they are your *paper* trading keys from `https://paper-api.alpaca.markets`
- ✓ Check Alpaca API status at `https://status.alpaca.markets`

**Email not sending:**
- ✓ Verify all three email secrets are set: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `EMAIL_RECIPIENT`
- ✓ Double-check the app password is exactly 16 characters (with spaces removed)
- ✓ Ensure 2FA is enabled on your Google Account (required for app passwords)
- ✓ Check GitHub Actions workflow run logs: Settings → Actions → HoneyDrip Daily Brief → latest run

**Brief doesn't show positions:**
- ✓ Confirm your paper trading account is active
- ✓ Verify you have open positions (equity > cash)
- ✓ Check Alpaca API status at `https://status.alpaca.markets`

**Email arrives but workflow shows "continue-on-error":**
- This is normal — the workflow completes even if email fails, so your brief is always saved
- Check the workflow logs to diagnose email issues (SMTP auth, server connectivity, etc.)
- The brief is always committed to git regardless of email success
