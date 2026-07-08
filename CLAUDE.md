# ImaginariumOzone — System Constraints & Build Plan

## Project Overview

This repository contains two independent components:

1. **Circle of Morality** (`src/`) — React UI, philosophical virtue-wheel application. Separate from trading infrastructure.
2. **HoneyDrip Bot** (`honeydrip_bot/`) — Python trading methodology framework. Alpaca Paper Trading only.

---

## Hard Rules (Non-Negotiable)

| Rule | Enforcement |
|------|-------------|
| `PAPER = True` always | Hard-coded in `honeydrip_bot/config.py` |
| `LIVE_TRADING_ENABLED = False` always | Hard-coded in `honeydrip_bot/config.py` and `engine.py` |
| Abort if `HONEYDRIP_ARMED != "YES"` | Double interlock: `config.py` + `engine.py` |
| API keys in env vars only | Never write keys to files, prompts, or dossiers |
| Alpaca for automation only | `alpaca_client.py` hard-codes paper endpoint |
| Robinhood for manual trades only | No programmatic Robinhood path exists or is authorized |

---

## Build Plan Phases

### Phase 1 — Manual Paper Trading (CURRENT)
- Execute trades manually on thinkorswim and Robinhood
- Log each trade via `honeydrip_bot/trade_logger.py`
- **Gate:** 20 trades must be logged before Phase 2 begins
- No automated execution of any kind during Phase 1

### Phase 2 — Programmatic Paper Validation (LOCKED until Phase 1 complete)
- Backtests and signal bridges run against Alpaca Paper Trading endpoints only
- All scripts must pass double interlock before executing
- `HONEYDRIP_ARMED=YES` must be set explicitly in the local shell environment

### Live-Readiness Gate (LOCKED)
- May not be assessed until Phase 2 is fully validated
- Requires separate authorization step
- Real capital is strictly prohibited until gate is passed

---

## Credential Rules

```
APCA_API_KEY_ID       — local env var, never committed
APCA_API_SECRET_KEY   — local env var, never committed
HONEYDRIP_ARMED       — set to YES only in a confirmed paper environment
```

Copy `honeydrip_bot/.env.example` to `honeydrip_bot/.env` locally and fill in values. The `.env` file is gitignored.

---

## Architectural Drift Assessment Reference

| Parameter | Authorized Constraint |
|-----------|----------------------|
| Execution Mode | Decision-support and accountability engine only. No auto-trading. |
| Platform Target | Alpaca Paper Trading for automation. Robinhood for manual execution only. |
| Operational Phase | PAPER phase. No live capital until Live-Readiness Gate is passed. |

---

## Running the Bot (Paper Mode Only)

```bash
# 1. Set required environment variables in your shell
export APCA_API_KEY_ID=your_paper_key
export APCA_API_SECRET_KEY=your_paper_secret
export HONEYDRIP_ARMED=YES

# 2. Install dependencies
pip install -r honeydrip_bot/requirements.txt

# 3. Run engine
python -m honeydrip_bot.engine
```

If `HONEYDRIP_ARMED` is not set to `YES`, the engine aborts immediately with an error.

---

## Running the React UI

```bash
npm install
npm run dev
# Opens at http://localhost:5173
```
