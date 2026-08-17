"""Hypothesis studies — RS-02 entry filters (spec §72; MARKET_THEORY queue).

Round 1 (2026-08-15, resolved): H1 52wk-high (both widths) NOISE;
H2a SPY-regime NOISE; H2b stock-above-own-200d ADOPTED into doctrine.
Round 2 (2026-08-16, resolved): H4a/H4b momentum-quality both
ADOPT-CANDIDATES with a dose-response pattern; operator ADOPTED H4b
(>= +10% 12-1 momentum). H6 spike guard: 5% NOISE, 8% REJECT.

Round 2 methodology (kept for the record) tested INCREMENTALLY on top
of the then-adopted doctrine —
every variant includes the H2b regime filter, and verdicts compare
against BASELINE_H2b, not the raw CONTROL. A filter only earns adoption
if it improves the system actually being run.

Round 3 (2026-08-16, resolved): H5 earnings blackout REJECTED. The
3-day variant was labelled ADOPT-CANDIDATE, but the margin came from
excluding 3 trades per window and those trades were PROFITABLE — total
return fell in both windows while the per-trade average rose. No
dose-response either. See the total-R columns below: they exist
because of H5.

Round 4 (2026-08-16, resolved on the operator's run): see the research
log for the H8 verdict.

Round 5 (current): three new inputs, each with its mechanism stated
before the data.

H9  news attention (Barber & Odean 2008 + the metaorder story): a
    breakout arriving in a burst of coverage is more crowded and more
    likely to fade than one accumulated quietly. SKIP high attention.
H10 profitability (Novy-Marx 2013): a breakout in an unprofitable name
    is more story than earnings and more prone to reversal. REQUIRE
    trailing-four-quarter profit, keyed to SEC FILING dates so nothing
    is known before it was public.
H11 overhead supply (volume-by-price): every share bought above today's
    price is a break-even seller the rally must absorb. REQUIRE clear
    air above. Worth testing where H1 and H3 failed because those were
    PRICE levels — this is a VOLUME measurement, genuinely new
    information rather than a restatement of the 20-day breakout.

Round 4 detail (kept for the record): H8 volatility regime — does requiring the VIX term
structure to be in contango (VIX / VIX3M below a threshold) improve
RS-02? Mechanism first: breakouts bet on continuation, and
backwardation is the market pricing near-term stress, which is when
continuation historically breaks (MARKET_THEORY momentum crashes).
Two pre-registered thresholds: ratio < 1.00 (skip backwardation only)
and ratio < 0.95 (require real contango).

Round-4 variants include the FULL adopted doctrine (H2b regime + H4b
quality) and verdicts compare against BASELINE_DOCTRINE. Requires the
term structure on disk: run `python -m mve.vix_regime` first (free,
no API key). The filter fails closed — a date with no VIX reading
blocks rather than assuming calm.

Adoption rule (pre-registered, LAW 12/20): beat BASELINE_DOCTRINE on
TRAIN and CONFIRM on TEST. Fewer trades with equal expectancy is NOT
an improvement.

    python -m mve.hypotheses
"""
from __future__ import annotations

import pandas as pd

# canonical impls live in setups — adopted filters cannot drift from
# the studied ones (H2b: above_sma; H4b: mom_12_1/quality_mom)
from datetime import date as _date

from .backtest import DATA_ROOT, run_backtest
from .earnings import load_earnings
from .fundamentals import is_profitable, load_fundamentals
from .news import load_news, quiet_attention
from .setups import above_sma, mom_12_1, quality_mom, rs02_entry_ok
from .store import DataStore
from .vix_regime import calm_regime, load_term_structure
from .volume_profile import clear_overhead, overhead_supply

TRAIN_END = "2024-12-31"
TEST_START = "2025-01-01"
HIGH_WINDOW = 252               # trailing sessions ~ 52 weeks
BASELINE = "BASELINE_DOCTRINE"  # round-3 comparison baseline
BLACKOUT_SHORT = 3              # calendar days ahead (entry into the print)
BLACKOUT_HOLD = 21              # calendar days ahead (whole expected hold)


def near_52wk_high(bars: pd.DataFrame, pct: float) -> bool:
    """Close within `pct` of the trailing 252-bar high (point-in-time).
    (Round 1: NOISE at both widths — kept for re-research.)"""
    highs = bars["high"].iloc[-HIGH_WINDOW:]
    return float(bars["close"].iloc[-1]) >= float(highs.max()) * (1.0 - pct)


def calm_breakout(bars: pd.DataFrame, max_gain: float) -> bool:
    """H6: the signal day's own return stays under `max_gain` — skip
    entries chasing a one-day spike. Fail-closed."""
    if len(bars) < 2:
        return False
    c = bars["close"]
    return float(c.iloc[-1]) / float(c.iloc[-2]) - 1.0 < max_gain


def earnings_clear(earnings: dict, ticker: str, bars, days_ahead: int) -> bool:
    """True when no earnings announcement falls within `days_ahead`
    calendar days AFTER the signal date. Tickers with no earnings on
    file pass untouched (ETFs; unfetched stocks — fetch first)."""
    dates = earnings.get(ticker)
    if not dates:
        return True
    d = _date.fromisoformat(str(bars["trade_date"].iloc[-1]))
    return not any(0 <= (e - d).days <= days_ahead for e in dates)


def signal_date(bars) -> str:
    return str(bars["trade_date"].iloc[-1])


def build_variants(news: dict, facts: dict) -> dict:
    """Round 5. Each variant is the FULL adopted doctrine plus one new
    filter, so a verdict is about that filter and nothing else."""
    return {
        "CONTROL":           None,                    # context only
        "BASELINE_DOCTRINE": lambda t, b, s: rs02_entry_ok(b),
        "H9a_quiet_news_2x": lambda t, b, s: (
            rs02_entry_ok(b) and quiet_attention(news, t, signal_date(b), 2.0)),
        "H9b_quiet_news_3x": lambda t, b, s: (
            rs02_entry_ok(b) and quiet_attention(news, t, signal_date(b), 3.0)),
        "H10_profitable": lambda t, b, s: (
            rs02_entry_ok(b) and is_profitable(facts, t, signal_date(b))),
        "H11a_overhead_10pct": lambda t, b, s: (
            rs02_entry_ok(b) and clear_overhead(b, 0.10)),
        "H11b_overhead_20pct": lambda t, b, s: (
            rs02_entry_ok(b) and clear_overhead(b, 0.20)),
    }


VARIANT_NAMES = ("CONTROL", "BASELINE_DOCTRINE",
                 "H9a_quiet_news_2x", "H9b_quiet_news_3x", "H10_profitable",
                 "H11a_overhead_10pct", "H11b_overhead_20pct")


def run_hypotheses(store: DataStore, setup: str = "RS-02",
                   news: dict | None = None,
                   facts: dict | None = None) -> dict:
    if news is None:
        news = load_news()
        if not news:
            raise SystemExit("No news counts on disk. Run: python -m mve.news")
    if facts is None:
        facts = load_fundamentals()
        if not facts:
            raise SystemExit("No fundamentals on disk. "
                             "Run: python -m mve.fundamentals")
    out = {}
    for name, f in build_variants(news, facts).items():
        train = run_backtest(store, end=TRAIN_END, active=(setup,),
                             entry_filter=f)
        test = run_backtest(store, start=TEST_START, active=(setup,),
                            entry_filter=f)
        out[name] = {
            "train": train.per_setup().get(setup),
            "test": test.per_setup().get(setup),
            "filtered": train.filtered_signals + test.filtered_signals,
            "by_ticker": _merge_by_ticker(train.per_ticker(setup),
                                          test.per_ticker(setup)),
        }
    return out


MIN_TICKER_TRADES = 5           # below this a per-ticker read is noise


def _merge_by_ticker(train: dict, test: dict) -> dict:
    """Combine both windows per ticker — breadth is about the whole
    history, not one window's slice of it."""
    out = {}
    for ticker in set(train) | set(test):
        a, b = train.get(ticker), test.get(ticker)
        n = (a["trades"] if a else 0) + (b["trades"] if b else 0)
        total = ((a["trades"] * a["expectancy_r"]) if a else 0.0) + \
                ((b["trades"] * b["expectancy_r"]) if b else 0.0)
        out[ticker] = {"trades": n,
                       "expectancy_r": round(total / n, 3) if n else 0.0}
    return out


def breadth_vs_baseline(variant: dict, baseline: dict) -> tuple:
    """(improved, compared) ticker counts, over names with enough trades
    in BOTH arms to be worth comparing."""
    improved = compared = 0
    for ticker, base in baseline.items():
        got = variant.get(ticker)
        if not got or base["trades"] < MIN_TICKER_TRADES \
                or got["trades"] < MIN_TICKER_TRADES:
            continue
        compared += 1
        if got["expectancy_r"] > base["expectancy_r"]:
            improved += 1
    return improved, compared


def total_r(s) -> float:
    """Sum of R across the window. Expectancy-per-trade alone can rise
    while total return falls — that is how H5 nearly earned adoption."""
    return 0.0 if s is None else s["trades"] * s["expectancy_r"]


def summary(results: dict) -> str:
    lines = ["HYPOTHESIS STUDY — RS-02 entry filters, round 5 "
             "(H9 news / H10 fundamentals / H11 volume, §72)",
             f"train <= {TRAIN_END} | test >= {TEST_START} | "
             f"verdicts vs {BASELINE} (adopted doctrine)", ""]

    def fmt(s):
        if s is None:
            return "n=  0  exp=   n/a  wr=n/a  totR=   n/a"
        return (f"n={s['trades']:>3} exp={s['expectancy_r']:+.3f}R "
                f"wr={s['win_rate']:.0%} totR={total_r(s):+7.2f}")

    for name, r in results.items():
        lines.append(f"{name:<21} train: {fmt(r['train'])}   "
                     f"test: {fmt(r['test'])}")
    lines.append("")

    base = results.get(BASELINE, {})
    bt, bs = base.get("train"), base.get("test")
    if bt and bs:
        lines.append(f"Verdicts vs {BASELINE} (adopt only if TRAIN improves "
                     "AND TEST confirms; small n = inconclusive):")
        for name, r in results.items():
            if name in ("CONTROL", BASELINE):
                continue
            t, s = r["train"], r["test"]
            if not t or not s or t["trades"] < 20 or s["trades"] < 10:
                lines.append(f"  {name}: INCONCLUSIVE (insufficient trades)")
                continue
            train_up = t["expectancy_r"] > bt["expectancy_r"]
            test_up = s["expectancy_r"] > bs["expectancy_r"]
            verdict = ("ADOPT-CANDIDATE" if train_up and test_up
                       else "REJECT (train did not improve)" if not train_up
                       else "NOISE (train improved, test did not confirm)")
            lines.append(f"  {name}: {verdict}")

            # H5 lesson, now automatic: a filter can raise the per-trade
            # average purely by deleting profitable-but-below-average
            # trades. Surface that instead of leaving it to be noticed.
            dn = (bt["trades"] - t["trades"]) + (bs["trades"] - s["trades"])
            dr = (total_r(bt) - total_r(t)) + (total_r(bs) - total_r(s))
            if verdict == "ADOPT-CANDIDATE":
                if dr > 0:
                    lines.append(
                        f"      CAUTION: removed {dn} trades worth "
                        f"{dr:+.2f}R of TOTAL return "
                        f"({dr / dn:+.3f}R each) — the average rose while "
                        "the total fell.")
                if dn <= 8:
                    lines.append(
                        f"      CAUTION: only {dn} trades differ from "
                        "baseline across both windows — too few to be "
                        "distinguishable from noise.")

            # Cross-sectional breadth: does it help most NAMES, or is the
            # aggregate being carried by a couple of lucky tickers?
            improved, compared = breadth_vs_baseline(
                r.get("by_ticker", {}), base.get("by_ticker", {}))
            if compared:
                lines.append(f"      breadth: improved {improved}/{compared} "
                             f"tickers (>= {MIN_TICKER_TRADES} trades each)")
                if verdict == "ADOPT-CANDIDATE" and improved * 2 < compared:
                    lines.append(
                        "      CAUTION: helps a MINORITY of tickers — the "
                        "aggregate gain is concentrated, not broad.")
            else:
                lines.append("      breadth: not comparable "
                             f"(no ticker has >= {MIN_TICKER_TRADES} trades "
                             "in both arms)")
    lines.append("")
    lines.append("LAW 12/20: no filter is adopted from a single pass alone — "
                 "an ADOPT-CANDIDATE gets encoded only by operator decision. "
                 "Read the CAUTION lines before deciding.")
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill")
    from .report import save_and_print
    save_and_print("hypotheses", summary(run_hypotheses(store)))
