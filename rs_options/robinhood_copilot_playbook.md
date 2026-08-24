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

Exit doctrine per the 2026-08-15 exit-policy study ("wide" won on train
AND confirmed on test; the old 2R/10-day baseline nearly zeroed out on
recent data). For every open options position from `data/executions.jsonl`:
1. Fetch the underlying's current price
2. If it closed below the pick's `invalidation_price` → sell (limit at
   mid), log the exit with realized P&L
3. If the underlying reached the pick's +3R level (entry + 3 × (entry −
   invalidation)) → sell and log — target reached
4. If the position is 15 trading days old → sell at the close — time exit
5. If DTE ≤ 5 → sell (never ride long premium into the final week —
   CALIBRATE)
6. Otherwise hold and report: position, P&L, distance to invalidation

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
| Volatility ETPs (VXX, UVXY, and kin) | **NO long premium, ever** — these products decay structurally (contango roll), so long calls fight a built-in downward drift on top of theta. Mechanism-based rule, adopted 2026-08-16 after broker-history forensics (18 VXX trades, 67% win rate, −$857). |
| Order type | Limit at mid, day only |

**The one deliberate exception: micro-account override (paper only).**
At paper equity under $500 — the size where 1%/5% sizing returns zero
shares for nearly the whole universe — set `RS_MICRO_ACCOUNT_OVERRIDE=YES`
to let the evening run buy exactly one affordable share instead of
skipping the trade. This is NOT doctrine: none of the backtests,
holdouts, or robustness figures in this program were measured under
it, every trade it places is tagged `micro_override` in the ledger and
printed in the report with the fraction of the account it commits, and
it never touches options (a single doctrine-compliant contract needs
roughly 100x a $500 account regardless of this setting). It exists
because at this account size the honest choice is "one full share,
sized by cash on hand" or "no trade" — see `paper/micro_sizing.py` for
the reasoning and `docs/RESEARCH_LOG.md` (2026-08-24) for why it was
built rather than just tuning `MAX_POSITION_PCT`. Turn it off, or grow
the account past $500, and the run reverts to validated sizing with no
other change needed.

## Active setups (§60 Level 2 — setup kill)

The live scan honors `mve/setups.py :: ACTIVE_SETUPS`. Current doctrine:

| Setup | Status | Evidence (5y daily-bar backtest, 2026-08-14) |
|---|---|---|
| RS-02 breakout | **ACTIVE** | +0.25R/trade over 160 trades, max DD −4.4R (in-sample) |
| RS-01 weakness absorption | **KILLED** | −0.145R/trade over 234 trades, max DD −47R |

Do not re-enable RS-01 by editing the tuple ad hoc. It earns its way back
only when a re-parameterized version shows positive OUT-OF-SAMPLE
expectancy in the backtester (LAW 20). Research tools still evaluate it.

**RS-02 entry conditions (adopted §72 filters):** at signal time the
stock must be

1. **above its own 200-day moving average** (H2b, adopted 2026-08-15 —
   train +0.415R vs +0.346R, test +0.239R vs +0.229R), and
2. **up at least +10% over the trailing 12 months**, measured to one
   month ago (H4b, adopted 2026-08-16 — vs the H2b baseline: train
   +0.516R vs +0.415R, test +0.324R vs +0.239R, with a dose-response
   pattern across thresholds).

Both fail closed: a ticker with under ~13 months of history produces no
entries. Expect roughly half as many signals as before H4b — fewer,
better trades. The scanner enforces both in `mve/setups.py ::
ENTRY_FILTERS` — no manual check needed, but if a breakout candidate is
missing from a scan, these are the first reasons to suspect.

**RS-02 fill condition — the 2% gap cap (H15a, adopted 2026-08-23).**
The two filters above run at signal time. This one runs the next
morning, at the fill:

> **Do not pay more than 2% above the signal close.** If the stock opens
> higher than that, abandon the trade. Do not chase it.

The paper trader enforces this automatically by placing the entry as a
**limit order at close × 1.02** instead of a market order, and reports
every cancellation under `H15a GAP CANCELLATIONS`. In Robinhood you
enforce it by hand: the scan report prints the exact limit price beside
each pick — if the pre-market or opening price is above it, skip that
name for the day.

Why this one and not the twenty other ideas that were tested: it is the
only rule found that removes LOSING trades. Every other filter tried
removed profitable ones. It is also not a market prediction — it is an
execution rule. Your stop sits at a fixed swing low, so an entry 3%
higher makes 1R wider before the trade has started, and you are risking
more to make the same move.

Evidence (H20 holdout on 2006–2020, data that never touched the window
where the 2% number was chosen): expectancy +0.117R vs +0.096R and total
+42.94R vs +36.10R over 9 cancelled fills. The 2%+ bucket lost money in
every window ever measured.

Honest caveat, so you are not surprised later: the effect is a **cliff**
at 2%, not a smooth slope — gapping up 1% was fine, even good. That is a
slightly different pattern than predicted before the test, so
`docs/PREREGISTERED.md` (FWD-2) tracks whether it keeps working going
forward. Roughly one order in fifty gets cancelled by it.

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
