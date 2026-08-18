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
python -m mve.backfill --years 20   # deep history: more statistical power,
                                    # spans 2008 and 2020 regimes
python -m mve.backtest              # replay RS-01/RS-02 across history
python -m mve.backtest 2023-01-01   # restrict the date range
```

What it validates: the RS setup signal on the **underlying**, in
R-multiples, point-in-time (signals fire on close, entries fill at the
next open, stop wins same-bar ties). What it cannot validate: options
P&L — historical chains are paid data. Results are the first hurdle of
the §72 experiment matrix, not a green light (LAW 19/20).

## Research studies (after backfill)

```bash
python -m mve.walkforward           # §51: does the RS-02 edge hold per period?
python -m mve.exit_study            # §41-§42: exit policies incl. H3 avwap_trail
python -m mve.earnings              # earnings dates (ALPHAVANTAGE_API_KEY)
python -m mve.vix_regime            # VIX/VIX3M term structure (free, no key)
python -m mve.news                  # daily article counts (APCA_* env keys);
                                    # re-run to fill gaps, --refresh to redo
python -m mve.fundamentals          # SEC EDGAR filings (needs
                                    # SEC_CONTACT_EMAIL — the SEC 403s
                                    # without a contact address)
python -m mve.hypotheses            # §72 rounds 5-6: H9 news, H10 fundamentals,
                                    # H11 volume, H13 vol-contraction, H14 close
                                    # strength, H15 gap cost, H16 clustering
python -m mve.exit_study            # now includes H12 partial exits
python -m mve.trade_journal         # broker-history stats (Schwab/TOS CSV
                                    # in data/ — stays local, gitignored)
python -m mve.alpaca_data           # Alpaca daily bars (APCA_* env keys)
python -m mve.alpaca_data --minute  # Alpaca minute bars, ~60d (intraday research)
python -m mve.alpaca_data --minute-deep   # ~2y minute bars, SPY/QQQ (H7)
python -m mve.intraday_study        # H7: ORB + intraday momentum, train/test
```

Exit-study discipline: pick the winning policy on TRAIN (≤ 2024),
confirm on TEST (≥ 2025). If they disagree, the improvement is noise —
keep the baseline (LAW 12/20).

Every study also saves its summary to `docs/reports/<name>.txt`. Commit
and push that folder after a run so the cloud session can read results
straight from the repo:

```bash
git add docs/reports && git commit -m "research reports" && git push
```

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

## Volatility regime (H8)

```bash
python -m mve.vix_regime            # fetch VIX/VIX3M, print the regime
```

Free, no API key (CBOE CSV, Yahoo fallback). The ratio VIX / VIX3M
below 1.0 is contango (calm); at or above 1.0 is backwardation — the
market pricing near-term stress, historically where momentum
continuation breaks. Regime CONTEXT: it appears in the daily paper
report but gates nothing until `mve.hypotheses` judges H8 and the
operator adopts it.
