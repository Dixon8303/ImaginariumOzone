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

Round 6 (current): four more, each in a dimension nothing else touches.

H13 volatility contraction — where does today's ATR sit in its own
    1-year range? Mechanism (Minervini's VCP, made mechanical): a
    breakout out of a QUIET base gives a tight stop and a fresh move,
    so more reward per unit risk. Nothing in the system currently
    measures stock-level volatility at all.
H14 close strength — where in the day's range did it close? A breakout
    closing at the high shows demand persisting into the bell; one
    closing mid-range shows sellers meeting it.
H15 gap cost — an EXECUTION test, not a prediction. Entries fill at the
    next open; if that open gaps far above the signal close you paid up
    and your R is worse before the trade starts. Implemented in the
    backtester as an order cancellation, which is what a real desk does.
H16 signal clustering — the first SET-level question asked here. When
    many names fire the same day, is that broad strength or a crowded
    top? Both stories are plausible, which is exactly when it is
    tempting to decide after seeing the answer, so the direction is
    pre-registered: crowding is the risk, so the filter SKIPS days with
    unusually many simultaneous signals.

MULTIPLE COMPARISONS: this study now runs many variants. Roughly one in
twenty independent tests passes by luck alone, so the summary prints an
expected false-positive count. Read it before believing any single
ADOPT-CANDIDATE — the more variants in a round, the more a lone winner
should be treated as a hypothesis to re-test, not a finding.

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
from .fundamentals import ETF_TICKERS, is_profitable, load_fundamentals
from .news import load_news, quiet_attention
from .setups import (MAX_ENTRY_GAP, above_sma, mom_12_1, quality_mom,
                     rs02_entry_ok)
from .store import DataStore
from .universe import BENCHMARK, UNIVERSE
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


MIN_COVERAGE = 0.95         # below this a data-backed verdict is biased


def data_coverage(data: dict, needed) -> tuple:
    """(covered, required, missing) for a per-ticker dataset.

    Filters that FAIL CLOSED turn missing data into a silent sample
    restriction: with news for 7 of 22 names, H9 would report a verdict
    about those 7 names while looking like a verdict about news. This is
    how a partial fetch becomes a fake finding, so coverage is measured
    and the affected variants are invalidated rather than scored.
    """
    required = sorted(needed)
    missing = [t for t in required if t not in data or _is_empty(data[t])]
    return len(required) - len(missing), len(required), missing


def _is_empty(frame) -> bool:
    try:
        return frame is None or len(frame) == 0
    except TypeError:
        return not frame


def signal_date(bars) -> str:
    return str(bars["trade_date"].iloc[-1])


def atr_percentile(bars: pd.DataFrame, length: int = 14,
                   window: int = 252) -> float | None:
    """H13: today's ATR as a percentile of its own trailing year.
    Low = quiet base. None (fail closed) without enough history."""
    if len(bars) < window + length:
        return None
    h, l, c = bars["high"], bars["low"], bars["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    atr_series = tr.rolling(length).mean().dropna()
    if len(atr_series) < window:
        return None
    recent = atr_series.iloc[-window:]
    return float((recent < atr_series.iloc[-1]).mean())


def quiet_base(bars: pd.DataFrame, max_pct: float) -> bool:
    """H13 filter: ATR percentile below `max_pct`. Fail-closed."""
    pct = atr_percentile(bars)
    return pct is not None and pct < max_pct


def close_strength(bars: pd.DataFrame) -> float | None:
    """H14: where the close sits in the day's range, 0 (low) to 1 (high).
    None for a zero-range bar — undefined, not zero."""
    bar = bars.iloc[-1]
    hi, lo, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
    if hi <= lo:
        return None
    return (close - lo) / (hi - lo)


def strong_close(bars: pd.DataFrame, min_strength: float) -> bool:
    """H14 filter: closed in the top of its range. Fail-closed."""
    strength = close_strength(bars)
    return strength is not None and strength >= min_strength


def uncrowded_day(counts: dict, trade_date: str, max_signals: int) -> bool:
    """H16 filter: fewer than `max_signals` names fired this day.
    A date absent from the map had no signals, which trivially passes."""
    return counts.get(trade_date, 0) <= max_signals


def daily_signal_counts(result) -> dict:
    """{date: how many signals fired} from a completed backtest."""
    counts: dict = {}
    for d in getattr(result, "signal_dates", []):
        counts[d] = counts.get(d, 0) + 1
    return counts


def build_variants(news: dict, facts: dict, counts: dict | None = None) -> dict:
    """Round 5. Each variant is the FULL adopted doctrine plus one new
    filter, so a verdict is about that filter and nothing else."""
    counts = counts or {}
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
        "H13a_quiet_base_40": lambda t, b, s: (
            rs02_entry_ok(b) and quiet_base(b, 0.40)),
        "H13b_quiet_base_60": lambda t, b, s: (
            rs02_entry_ok(b) and quiet_base(b, 0.60)),
        "H14a_close_top30": lambda t, b, s: (
            rs02_entry_ok(b) and strong_close(b, 0.70)),
        "H14b_close_top50": lambda t, b, s: (
            rs02_entry_ok(b) and strong_close(b, 0.50)),
        "H16a_max2_signals": lambda t, b, s: (
            rs02_entry_ok(b) and uncrowded_day(counts, signal_date(b), 2)),
        "H16b_max4_signals": lambda t, b, s: (
            rs02_entry_ok(b) and uncrowded_day(counts, signal_date(b), 4)),
    }


VARIANT_NAMES = ("CONTROL", "BASELINE_DOCTRINE",
                 "H9a_quiet_news_2x", "H9b_quiet_news_3x", "H10_profitable",
                 "H11a_overhead_10pct", "H11b_overhead_20pct",
                 "H13a_quiet_base_40", "H13b_quiet_base_60",
                 "H14a_close_top30", "H14b_close_top50",
                 "H16a_max2_signals", "H16b_max4_signals",
                 "H15a_gap_2pct", "H15b_gap_1pct")

# H15 is a fill-time cancellation, not a signal-time filter — it runs
# through the backtester's max_gap_pct rather than an entry_filter.
# H15a imports the live constant so an adopted rule and the study that
# judges it can never drift apart. H15b stays a fixed comparison arm.
GAP_VARIANTS = {"H15a_gap_2pct": MAX_ENTRY_GAP, "H15b_gap_1pct": 0.01}


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
    # H16 needs to know how many names fired each day, which is only
    # knowable after a pass. Counts come from the BASELINE run so the
    # clustering filter is judged against the same signal set it sees.
    base_train = run_backtest(store, end=TRAIN_END, active=(setup,),
                              entry_filter=lambda t, b, s: rs02_entry_ok(b))
    base_test = run_backtest(store, start=TEST_START, active=(setup,),
                             entry_filter=lambda t, b, s: rs02_entry_ok(b))
    counts = daily_signal_counts(base_train)
    counts.update(daily_signal_counts(base_test))

    def record(train, test):
        return {
            "train": train.per_setup().get(setup),
            "test": test.per_setup().get(setup),
            "filtered": train.filtered_signals + test.filtered_signals,
            "gapped": train.gapped_signals + test.gapped_signals,
            "by_ticker": _merge_by_ticker(train.per_ticker(setup),
                                          test.per_ticker(setup)),
        }

    # Coverage is checked BEFORE anything is scored, and recorded on the
    # affected variants so the summary can invalidate them.
    stocks = {t for t in UNIVERSE if t != BENCHMARK}
    news_cov = data_coverage(news, stocks)
    facts_cov = data_coverage(facts, stocks - ETF_TICKERS)

    out = {}
    for name, f in build_variants(news, facts, counts).items():
        train = run_backtest(store, end=TRAIN_END, active=(setup,),
                             entry_filter=f)
        test = run_backtest(store, start=TEST_START, active=(setup,),
                            entry_filter=f)
        out[name] = record(train, test)
        cov = (news_cov if name.startswith("H9")
               else facts_cov if name.startswith("H10") else None)
        if cov and cov[0] < cov[1] * MIN_COVERAGE:
            out[name]["invalid"] = (
                f"data covers only {cov[0]}/{cov[1]} tickers — this would "
                f"be a verdict about those names, not about the filter. "
                f"Missing: {', '.join(cov[2][:6])}"
                + ("..." if len(cov[2]) > 6 else ""))

    # H15 is a fill-time cancellation: the doctrine filter is unchanged
    # and the gap tolerance is passed to the backtester instead.
    doctrine = lambda t, b, s: rs02_entry_ok(b)          # noqa: E731
    for name, gap in GAP_VARIANTS.items():
        train = run_backtest(store, end=TRAIN_END, active=(setup,),
                             entry_filter=doctrine, max_gap_pct=gap)
        test = run_backtest(store, start=TEST_START, active=(setup,),
                            entry_filter=doctrine, max_gap_pct=gap)
        out[name] = record(train, test)

    # H15 diagnostic. Tested AS A FILTER, the gap rule only ever touches
    # a handful of trades, so its verdict rests on a sample too small to
    # separate from luck. The underlying claim — "paying up at the open
    # costs you" — is continuous, and every trade carries a gap. Measure
    # it across ALL of them: a real execution effect shows a monotone
    # decline across buckets, while six unlucky fills do not.
    out["_gap_dose"] = {
        "train": gap_buckets(run_backtest(store, end=TRAIN_END,
                                          active=(setup,),
                                          entry_filter=doctrine)),
        "test": gap_buckets(run_backtest(store, start=TEST_START,
                                         active=(setup,),
                                         entry_filter=doctrine)),
    }
    return out


GAP_BUCKETS = ((-1.0, 0.0, "gap DOWN / flat"),
               (0.0, 0.01, "up 0-1%"),
               (0.01, 0.02, "up 1-2%"),
               (0.02, 99.0, "up 2%+"))


def gap_buckets(result, setup: str = "RS-02") -> list:
    """Expectancy by entry-gap size across every trade, not just the few
    a threshold would remove."""
    rows = []
    trades = [t for t in result.trades if t.setup == setup]
    for lo, hi, label in GAP_BUCKETS:
        sel = [t for t in trades if lo <= t.gap_pct < hi]
        n = len(sel)
        tot = sum(t.r_multiple for t in sel)
        rows.append({"label": label, "trades": n,
                     "expectancy_r": round(tot / n, 3) if n else 0.0,
                     "total_r": round(tot, 2)})
    return rows


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

    variants = {k: v for k, v in results.items() if not k.startswith("_")}
    for name, r in variants.items():
        lines.append(f"{name:<21} train: {fmt(r['train'])}   "
                     f"test: {fmt(r['test'])}")
    lines.append("")

    base = results.get(BASELINE, {})
    bt, bs = base.get("train"), base.get("test")
    if bt and bs:
        lines.append(f"Verdicts vs {BASELINE} (adopt only if TRAIN improves "
                     "AND TEST confirms; small n = inconclusive):")
        for name, r in variants.items():
            if name in ("CONTROL", BASELINE):
                continue
            if r.get("invalid"):
                lines.append(f"  {name}: INVALID — {r['invalid']}")
                continue
            t, s = r["train"], r["test"]
            if not t or not s or t["trades"] < 20 or s["trades"] < 10:
                lines.append(f"  {name}: INCONCLUSIVE (insufficient trades)")
                continue
            # A filter that removed NOTHING was never exercised by this
            # sample. Calling that "REJECT" reads as tested-and-failed,
            # which is the exact silent failure this report exists to
            # prevent — the condition it guards against simply never
            # occurred, so the hypothesis is untested, not refuted.
            if (t["trades"] == bt["trades"]
                    and s["trades"] == bs["trades"]
                    and abs(total_r(t) - total_r(bt)) < 1e-9
                    and abs(total_r(s) - total_r(bs)) < 1e-9):
                lines.append(
                    f"  {name}: NO EFFECT — the filter never bound "
                    "(identical to baseline). The condition it screens "
                    "for does not occur in this sample; UNTESTED, not "
                    "refuted.")
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
    dose = results.get("_gap_dose")
    if dose:
        lines += ["",
                  "H15 DOSE-RESPONSE — expectancy by entry gap, ALL trades "
                  "(the filter above only touches a handful; this is the "
                  "same claim measured at full power):"]
        for window in ("train", "test"):
            lines.append(f"  {window}:")
            for row in dose[window]:
                lines.append(
                    f"    {row['label']:<16} n={row['trades']:>3} "
                    f"exp={row['expectancy_r']:+.3f}R "
                    f"totR={row['total_r']:+7.2f}")
        lines.append("  A real execution cost declines steadily across the "
                     "buckets in BOTH windows. A jagged or reversing "
                     "pattern means the filter's gain was a few outliers.")

    tested = max(0, len(variants) - 2)      # exclude CONTROL and BASELINE
    expected_false = tested * 0.05
    candidates = sum(1 for line in lines if line.strip().startswith(
        ("H", "  H")) and "ADOPT-CANDIDATE" in line)
    lines += ["",
              f"MULTIPLE COMPARISONS: {tested} variants tested this round. "
              f"At a 1-in-20 luck rate that is ~{expected_false:.1f} "
              "ADOPT-CANDIDATEs expected from chance alone."]
    if candidates and candidates <= expected_false + 1:
        lines.append(f"  The {candidates} candidate(s) here are within what "
                     "chance would produce — treat any of them as something "
                     "to RE-TEST on fresh data, not as a finding.")
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
