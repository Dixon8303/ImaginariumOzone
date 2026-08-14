# RS Options Co-Pilot — Robinhood MCP Playbook

**Mode: autonomous selection, human-confirmed execution.**
The engine chooses the trades — ticker, contract, size — across the full
universe. The operator's one job is the final word: "execute the pick list."
Unattended execution (no human word) stays locked until the engine has a
logged track record that passes the spec's release gate (§67).

Claude Code (local, with `robinhood-trading` MCP connected) follows this
playbook when the operator asks to **"run the options scan."**

---

## Daily scan

### 1. Fetch data (Robinhood MCP)

For every ticker in `mve/universe.py :: required_tickers()`:
- fetch ~120 daily bars (open/high/low/close/volume)

For every ticker in `UNIVERSE` (the tradeable names):
- fetch today's option chain — calls, expirations 7–45 days out, with
  bid/ask, volume, open interest, IV, delta

Write them as canonical CSVs (`bars_*.csv`, `chains_*.csv` in the schema
from `mve/store.py`) into a scratch directory, then ingest:

```python
from mve.store import DataStore
from mve.vendors import CsvVendor

store = DataStore("data/parquet")
vendor = CsvVendor("data/incoming")
store.ingest_bars(vendor.bars())
store.ingest_chains(vendor.chains())
```

If bars or chains for a ticker cannot be fetched, drop that ticker from
today's scan and say so — never substitute stale or guessed data (LAW 18).

### 2. Run the session (canary-first)

```python
from mve.session import run_research_session
from mve.telemetry import TelemetryLog
from mve.universe import BENCHMARK, SECTOR_ETF, UNIVERSE
from mve.picklist import build_picklist, format_picklist

telemetry = TelemetryLog("data/telemetry.jsonl")
result = run_research_session(
    store, universe=list(UNIVERSE), as_of="<today YYYY-MM-DD>",
    telemetry=telemetry, benchmark=BENCHMARK, sector_map=SECTOR_ETF,
    macro_csv="mve/data/macro_calendar.csv",
)
print(format_picklist(build_picklist(telemetry.records())))
```

If the canary suite fails (`CanaryFailure`), STOP — Level 0 halt (§61).
Report it; do not scan, do not trade.

### 3. Present the pick list

Show the operator the formatted pick list: contract, quantity, estimated
cost, worst-case loss, exit level, and the reason. If it is empty, say so —
NO TRADE is a valid outcome (§69), not a malfunction.

### 4. Execute — ONLY on the operator's explicit word

When (and only when) the operator says "execute" (all picks) or names
specific picks:

For each approved pick:
1. `get_account` → confirm buying power covers `est_cost`; re-size down if not
2. Fetch a fresh quote for the contract; if the ask moved more than 5%
   above the scanned price, skip the pick and report it (§39 re-check rule)
3. Place a **limit order at the mid**, day only — never a market order on
   options (§38: marketable sweeps prohibited)
4. Log every fill AND every skip to `data/executions.jsonl`:
   `{date, contract, qty, limit, fill_price, status, pick}`

Never exceed the pick's quantity. Never add tickers the scan did not
authorize. If any Robinhood call errors, stop and report — no retries.

---

## Position management (each scan day, before new picks)

For every open options position from `data/executions.jsonl`:
1. Fetch the underlying's current price
2. If it closed below the pick's `invalidation_price` → sell the position
   (limit at mid), log the exit with realized P&L
3. If DTE ≤ 5 → sell (never ride long premium into the final week —
   CALIBRATE)
4. Otherwise hold and report: position, P&L, distance to invalidation

---

## Hard limits (from the risk engine — never overridden here)

| Limit | Value |
|---|---|
| Max risk per trade | 1% of equity |
| Max per underlying | 5% of equity |
| Max per cluster (semis, megacap tech, …) | 10% of equity |
| Max daily loss | 3% → session HALT |
| Max drawdown | 10% → system FREEZE |
| Structures | Long calls only |
| Order type | Limit at mid, day only |

## Volatility context (the "volatility box")

Each scan computes an ATM-IV reading per ticker from the day's chain and
ranks it against the trailing history of prior scans (spec §23, §34).
For this long-premium engine, **rich IV is a headwind** — buying expensive
premium — so high IV Rank penalizes the candidate's score:

| IV Rank | Effect |
|---|---|
| unknown (< 20 recorded sessions) | no penalty — reported as "uncalibrated" |
| < 60 | no penalty |
| 60–80 | −1 score (rich premium) |
| > 80 | −2 score (extreme — §34) |

The gate activates automatically as scan history accumulates; do not
hand-enter IV values to force it. Premium *selling* in high IV remains
prohibited until short-structure margin adapters are validated (§8).

## Track record → autonomy

Every scan and execution accrues in telemetry. When the logged history is
long enough to evaluate against the §67 release gate (expectancy after
friction, drawdown, sample size), the operator may revisit unattended
execution. Until then, the human word before execution is a hard rule of
this playbook.
