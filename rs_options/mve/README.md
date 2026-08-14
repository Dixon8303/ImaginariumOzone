# mve — Minimum Viable Engine (spec §87)

The reduced build of roadmap Phases 1–3 for one operator, one box, one
process. Everything here serves the smallest honest test of the RS
hypothesis (§70). **No trading** — `run_research_session` accepts
RESEARCH/PAPER modes only and has no order-transmission path.

## Layout

| Module | Spec | Responsibility |
|---|---|---|
| `store.py` | §46 | DuckDB over partitioned Parquet; idempotent ingest; point-in-time reads; gap QA |
| `vendors.py` | §46 | Vendor seam: `CsvVendor` (drop normalized CSVs) + `SyntheticVendor` (deterministic test data) |
| `macro_calendar.py` | §11–§12 | Static CSV calendar → PRE_EVENT / EVENT_WINDOW / POST_EVENT → `MacroState` |
| `rs_features.py` | §13–§16 | Market/sector/beta-adjusted RS, persistence, relative volume |
| `setups.py` | §17 | RS-01 (weakness absorption) + RS-02 (RS breakout) detectors; §32 score rubric |
| `chain_select.py` | §18–§19, §27 | Long-call selection from EOD chains: Δ 0.40–0.80, DTE 7–45, spread ≤10% |
| `session.py` | §61, §81 | Canary-first session: canary → macro → scan → gate stack → telemetry |
| `telemetry.py` | §62–§63 | JSONL log of every evaluation (rejects included) + rejection-forensics aggregate |

## Run

```bash
cd rs_options
pip install -r mve/requirements.txt
python -m mve.demo                  # synthetic end-to-end session
python -m pytest tests/ -q          # full suite (risk engine + MVE)
```

## Backtest on real history (free data)

```bash
python -m mve.backfill              # ~5y of daily bars, full universe
                                    # (Stooq, Yahoo fallback — no API key)
python -m mve.backtest              # replay RS-01/RS-02 across history
python -m mve.backtest 2023-01-01   # restrict the date range
```

What it validates: the RS setup signal on the **underlying**, in
R-multiples, point-in-time (signals fire on close, entries fill at the
next open, stop wins same-bar ties). What it cannot validate: options
P&L — historical chains are paid data. Results are the first hurdle of
the §72 experiment matrix, not a green light (LAW 19/20).

## Feeding real data

Drop normalized CSVs (`bars_*.csv`, `chains_*.csv` in the canonical store
schema) into a directory and ingest via `CsvVendor` — that is the vendor
seam (§46 "bought, not built"). Keep `receipt_ts` discipline in mind when
graduating to intraday data; the daily bootstrap sidesteps it by being
strictly EOD.

## Boundaries

- Long premium, long calls only (§87 KEEP list).
- Every threshold is CALIBRATE. Detector thresholds, the score rubric, and
  chain filters are hypotheses for the §72 experiment matrix — not signals.
- A failed canary suite raises `CanaryFailure` and the session never scans
  (§61: Level 0 halt).
- Graduation triggers (§87): DuckDB→ClickHouse when queries take minutes;
  more setups only after RS-01/RS-02 have verdicts; spreads only after a
  broker margin adapter is validated in Shadow.
