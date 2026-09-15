# HoneyDrip Daily Brief Setup

Automated daily email reports of your trading activity: positions, P&L, signals, and performance metrics.

## One-Time Setup

### 1. Store Alpaca credentials in GitHub Secrets

The workflow needs your paper trading credentials to fetch account data:

```bash
# On GitHub.com: Settings → Secrets and Variables → Actions → New repository secret

# Add these two secrets:
APCA_API_KEY_ID=<your_paper_key_id>
APCA_API_SECRET_KEY=<your_paper_secret>
```

Never commit these to the repository.

### 2. Set up daily email delivery (Claude Code)

The workflow generates the brief and commits it to the repo. To have it emailed to you automatically:

```bash
# In Claude Code with Gmail MCP connected:

# Run this command once:
/brief-email-routine

# This creates a daily Routine that:
# - Reads the latest brief from honeydrip_bot/briefs/
# - Formats it as an email
# - Sends it to your inbox at 8:15 AM UTC (Mon-Fri)
```

Or set it up manually via Claude Code:

```
Create a Routine named "HoneyDrip Daily Brief" that fires at 8:15 AM UTC Mon-Fri.
The Routine should read honeydrip_bot/briefs/<today's date>.txt, format it as an
email, and send it to eatmediatv@gmail.com via Gmail MCP. Use the brief's content
as the email body and title it "HoneyDrip Daily Brief — <date>".
```

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

## Manual Brief Generation

To generate a brief on-demand:

```bash
export APCA_API_KEY_ID=<your_paper_key>
export APCA_API_SECRET_KEY=<your_paper_secret>
export HONEYDRIP_ARMED=YES

python -m honeydrip_bot.daily_brief
```

Briefs are saved to `honeydrip_bot/briefs/` and committed to git history for long-term tracking.

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

**Workflow fails with auth error:**
- Verify `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` are set in GitHub Secrets
- Ensure they are your *paper* trading keys (from `https://paper-api.alpaca.markets`)

**Brief doesn't show positions:**
- Confirm trading account is active and has open positions
- Check Alpaca API status at `https://status.alpaca.markets`

**Email not arriving:**
- Confirm the Claude Code Routine was created successfully
- Check Gmail's "All Mail" folder (may be filtered as automated)
- Verify the Routine's last run status in Claude Code's Routines list
