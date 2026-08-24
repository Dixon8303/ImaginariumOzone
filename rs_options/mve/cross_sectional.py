"""Cross-sectional momentum, long only (H-22, §72).

Implements `docs/PREREGISTERED.md :: H-22` exactly as frozen on
2026-08-23, in a commit that lands AFTER the registration. Every
parameter below is copied from that entry; none is chosen here. If a
number in this module disagrees with the registration, the registration
is right and this module is a bug.

The claim (Jegadeesh & Titman 1993): rank assets against EACH OTHER and
the leaders keep leading. This is a different bet from RS-02 — relative
rather than absolute, calendar-driven rather than event-driven,
continuously invested rather than episodic, and with no stop.

Because there is no stop there is no R, so nothing here is quoted in
R-multiples: doing so would invite a false comparison against RS-02's
+0.117R. Measurement is portfolio-level, against the only honest bar
for a long-only near-always-invested strategy — SPY buy-and-hold over
the identical window, costs included.

Costs, per the registration, are charged rather than gross. A name
carried across a rebalance pays nothing; only entries and exits do.
Stated limitation: equal-weight drift is not re-charged, so the figure
here is slightly OPTIMISTIC on cost. It is reported alongside turnover
so the size of that omission is visible.

    python -m mve.cross_sectional
"""
from __future__ import annotations

from .backtest import DATA_ROOT
from .robustness import REALISTIC_BPS
from .setups import MOM_LOOKBACK, above_sma, mom_12_1
from .store import DataStore
from .universe import BENCHMARK, UNIVERSE

# The registration says "the 21 non-benchmark tickers already in
# mve/universe.py". UNIVERSE actually holds 22, none of them the
# benchmark — the 21 was a miscount in the registration, not a
# different universe. The binding intent is "the existing universe, no
# additions and no substitutions", which is what is used here. Recorded
# rather than quietly corrected, because silently reconciling a
# registration to the code is how pre-registration stops meaning
# anything.

# ── frozen by the registration; do not tune ──────────────────────────
TOP_N_ARMS = (3, 5)              # two arms, equal weight
TRAIN_END = "2020-12-31"
TEST_START = "2021-01-01"
MIN_REBALANCES = 60              # below this: INCONCLUSIVE, no verdict
COST_BPS = REALISTIC_BPS         # charged, never gross
MONTHS_PER_YEAR = 12


def rebalance_dates(dates: list) -> list:
    """First trading day of each month present in the data."""
    seen, out = set(), []
    for d in dates:
        key = str(d)[:7]
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def _indexed(store: DataStore, tickers) -> dict:
    frames = {}
    for t in tickers:
        bars = store.bars(t)
        if bars is not None and not bars.empty:
            frames[t] = bars.reset_index(drop=True)
    return frames


def _load(store: DataStore) -> dict:
    """Universe PLUS the benchmark. UNIVERSE excludes the benchmark, so
    loading it alone leaves no SPY frame and every window returns empty
    — a silent nothing rather than an error. Caught by the tests; the
    guard below makes the failure loud if it ever recurs."""
    frames = _indexed(store, list(UNIVERSE) + [BENCHMARK])
    if BENCHMARK not in frames:
        raise SystemExit(
            f"No {BENCHMARK} bars on disk. The benchmark is required — it "
            "defines the monthly grid AND is the registered comparison. "
            "Run: python -m mve.backfill --years 20")
    return frames


def rank_and_select(frames: dict, asof: str, top_n: int) -> list:
    """Top `top_n` eligible names by 12-1 momentum, ranked on data
    STRICTLY BEFORE `asof` — the fill happens at that day's open, so
    using the day's own close would be lookahead."""
    scored = []
    for ticker, bars in frames.items():
        if ticker == BENCHMARK:
            continue
        prior = bars[bars["trade_date"] < asof]
        if len(prior) < MOM_LOOKBACK + 1:
            continue
        if not above_sma(prior):              # adopted doctrine eligibility
            continue
        m = mom_12_1(prior)
        if m is None:
            continue
        scored.append((m, ticker))
    scored.sort(reverse=True)
    return [t for _, t in scored[:top_n]]


def _open_on(bars, date: str) -> float | None:
    row = bars[bars["trade_date"] == date]
    return float(row["open"].iloc[0]) if len(row) else None


def run_arm(frames: dict, top_n: int, start: str | None, end: str | None,
            cost_bps: float = COST_BPS) -> dict:
    """One arm over one window. Returns monthly returns, turnover and
    the resulting portfolio statistics."""
    bench = frames.get(BENCHMARK)
    if bench is None:
        return {}
    dates = [d for d in bench["trade_date"]
             if (start is None or d >= start) and (end is None or d <= end)]
    rebals = rebalance_dates(dates)
    if len(rebals) < 2:
        return {}

    c = cost_bps / 10_000.0
    held, monthly, turnovers = [], [], []
    for i in range(len(rebals) - 1):
        asof, nxt = rebals[i], rebals[i + 1]
        target = rank_and_select(frames, asof, top_n)

        # Period return: equal weight across held names, cash earns 0.
        # An empty book (nothing above its 200-day SMA) is fully in cash,
        # which is a real outcome of the rule, not a missing datum.
        rets = []
        for t in target:
            bars = frames[t]
            o0, o1 = _open_on(bars, asof), _open_on(bars, nxt)
            if o0 and o1:
                rets.append(o1 / o0 - 1.0)
        gross = (sum(rets) / len(target)) if target and rets else 0.0

        # Only names entering or leaving trade. Carried names pay
        # nothing — which is exactly why turnover is worth reporting.
        changed = len(set(target) ^ set(held))
        denom = max(len(target), len(held), 1)
        turnover = changed / denom
        monthly.append(gross - turnover * 2.0 * c)
        turnovers.append(turnover)
        held = target

    return _stats(monthly, turnovers, len(rebals) - 1)


def eligible_counts(frames: dict, start: str | None,
                    end: str | None) -> dict:
    """How many names pass the filter at each rebalance. If the mean is
    near the arm size, "top 3 of the universe" is not selecting
    anything — it is holding whatever qualified."""
    bench = frames.get(BENCHMARK)
    dates = [d for d in bench["trade_date"]
             if (start is None or d >= start) and (end is None or d <= end)]
    counts = []
    for asof in rebalance_dates(dates):
        n = 0
        for ticker, bars in frames.items():
            if ticker == BENCHMARK:
                continue
            prior = bars[bars["trade_date"] < asof]
            if len(prior) >= MOM_LOOKBACK + 1 and above_sma(prior):
                n += 1
        counts.append(n)
    if not counts:
        return {}
    return {"mean": sum(counts) / len(counts),
            "min": min(counts), "max": max(counts),
            "empty_months": sum(1 for n in counts if n == 0)}


def universe_buy_hold(frames: dict, start: str | None, end: str | None,
                      cost_bps: float = COST_BPS) -> dict:
    """THE CONTROL THAT MATTERS, added after the run as a DIAGNOSTIC.

    Hold EVERY eligible name, equal weight, on the same monthly grid —
    the identical machinery with the RANKING REMOVED. The universe is 22
    tickers chosen in 2026, and it contains several of the largest
    winners of the period. Ranking within a basket of known winners will
    look spectacular whether or not ranking adds anything, so the only
    way to separate "momentum selection works" from "these 22 stocks
    went up" is to run the version that selects nothing.

    Added post-hoc, which is only defensible because it can make the
    result look WORSE or reveal it as artifact — never rescue it. A
    post-hoc check that could rescue a failed result would be
    p-hacking; this one cannot.
    """
    bench = frames.get(BENCHMARK)
    if bench is None:
        return {}
    dates = [d for d in bench["trade_date"]
             if (start is None or d >= start) and (end is None or d <= end)]
    rebals = rebalance_dates(dates)
    if len(rebals) < 2:
        return {}
    c = cost_bps / 10_000.0
    held, monthly, turnovers = [], [], []
    for i in range(len(rebals) - 1):
        asof, nxt = rebals[i], rebals[i + 1]
        target = [t for t in frames
                  if t != BENCHMARK
                  and len(frames[t][frames[t]["trade_date"] < asof])
                  >= MOM_LOOKBACK + 1
                  and above_sma(frames[t][frames[t]["trade_date"] < asof])]
        rets = []
        for t in target:
            o0, o1 = _open_on(frames[t], asof), _open_on(frames[t], nxt)
            if o0 and o1:
                rets.append(o1 / o0 - 1.0)
        gross = (sum(rets) / len(target)) if target and rets else 0.0
        changed = len(set(target) ^ set(held))
        turnover = changed / max(len(target), len(held), 1)
        monthly.append(gross - turnover * 2.0 * c)
        turnovers.append(turnover)
        held = target
    return _stats(monthly, turnovers, len(rebals) - 1)


def buy_hold(frames: dict, start: str | None, end: str | None,
             cost_bps: float = COST_BPS) -> dict:
    """SPY buy-and-hold on the same monthly grid, costs included. The
    registered benchmark."""
    bench = frames.get(BENCHMARK)
    if bench is None:
        return {}
    dates = [d for d in bench["trade_date"]
             if (start is None or d >= start) and (end is None or d <= end)]
    rebals = rebalance_dates(dates)
    if len(rebals) < 2:
        return {}
    c = cost_bps / 10_000.0
    monthly = []
    for i in range(len(rebals) - 1):
        o0, o1 = _open_on(bench, rebals[i]), _open_on(bench, rebals[i + 1])
        monthly.append(o1 / o0 - 1.0 if o0 and o1 else 0.0)
    if monthly:                       # one round trip across the window
        monthly[0] -= c
        monthly[-1] -= c
    return _stats(monthly, [0.0] * len(monthly), len(rebals) - 1)


def _stats(monthly: list, turnovers: list, periods: int) -> dict:
    if not monthly:
        return {}
    equity, curve = 1.0, [1.0]
    for r in monthly:
        equity *= (1.0 + r)
        curve.append(equity)
    years = len(monthly) / MONTHS_PER_YEAR
    cagr = (equity ** (1.0 / years) - 1.0) if years > 0 and equity > 0 else 0.0

    mean = sum(monthly) / len(monthly)
    if len(monthly) > 1:
        var = sum((r - mean) ** 2 for r in monthly) / (len(monthly) - 1)
        sharpe = ((mean / var ** 0.5) * (MONTHS_PER_YEAR ** 0.5)
                  if var > 0 else None)
    else:
        sharpe = None

    peak, dd = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1.0)

    return {"periods": periods, "months": len(monthly),
            "total_return": equity - 1.0, "cagr": cagr, "sharpe": sharpe,
            "max_drawdown": dd,
            "turnover": (sum(turnovers) / len(turnovers)) if turnovers
            else 0.0}


def run_h22(store: DataStore) -> dict:
    frames = _load(store)
    windows = {"train": (None, TRAIN_END), "test": (TEST_START, None)}
    out = {"arms": {}, "benchmark": {}, "no_selection": {},
           "eligible": {}}
    for label, (s, e) in windows.items():
        out["benchmark"][label] = buy_hold(frames, s, e)
        out["no_selection"][label] = universe_buy_hold(frames, s, e)
        out["eligible"][label] = eligible_counts(frames, s, e)
        for n in TOP_N_ARMS:
            out["arms"].setdefault(f"top{n}", {})[label] = run_arm(
                frames, n, s, e)
    return out


def _fmt(s: dict) -> str:
    if not s:
        return "no data"
    sh = f"{s['sharpe']:.2f}" if s.get("sharpe") is not None else " n/a"
    return (f"n={s['months']:>3}mo  CAGR {s['cagr']:>+7.2%}  "
            f"Sharpe {sh:>5}  maxDD {s['max_drawdown']:>+7.2%}  "
            f"turnover {s['turnover']:>5.0%}")


def verdict(arm: dict, bench: dict) -> tuple:
    """The registered criteria, applied literally."""
    train, test = arm.get("train") or {}, arm.get("test") or {}
    btr, bte = bench.get("train") or {}, bench.get("test") or {}
    total = train.get("periods", 0) + test.get("periods", 0)
    if total < MIN_REBALANCES:
        return ("INCONCLUSIVE",
                f"{total} rebalances, under the registered minimum of "
                f"{MIN_REBALANCES} — no verdict regardless of the numbers")
    for label, a, b in (("train", train, btr), ("test", test, bte)):
        if a.get("sharpe") is None or b.get("sharpe") is None:
            return ("INCONCLUSIVE", f"{label} Sharpe not computable")
        if a["sharpe"] <= b["sharpe"]:
            return ("FAILED",
                    f"{label} Sharpe {a['sharpe']:.2f} does not exceed "
                    f"SPY's {b['sharpe']:.2f}")
    for label, a, b in (("train", train, btr), ("test", test, bte)):
        if a["max_drawdown"] < b["max_drawdown"]:
            return ("FAILED",
                    f"{label} drawdown {a['max_drawdown']:.1%} is worse "
                    f"than SPY's {b['max_drawdown']:.1%}")
    return ("CONFIRMED", "beat SPY on Sharpe in both windows with no "
                         "worse drawdown")


def summary(results: dict) -> str:
    bench = results["benchmark"]
    lines = [
        "CROSS-SECTIONAL MOMENTUM, LONG ONLY (H-22, §72)",
        f"train <= {TRAIN_END} | test >= {TEST_START} | "
        f"costs {COST_BPS:.0f}bp | monthly rebalance",
        "",
        "Implements docs/PREREGISTERED.md :: H-22 as frozen. No parameter",
        "was chosen here; ranking reuses the adopted mom_12_1 and",
        "eligibility the adopted 200-day SMA.",
        "",
        "BENCHMARK — SPY buy-and-hold, same grid, costs included:",
        f"  train  {_fmt(bench.get('train'))}",
        f"  test   {_fmt(bench.get('test'))}",
    ]
    for name, arm in results["arms"].items():
        v, why = verdict(arm, bench)
        lines += ["", f"{name.upper()} (equal weight):",
                  f"  train  {_fmt(arm.get('train'))}",
                  f"  test   {_fmt(arm.get('test'))}",
                  f"  VERDICT: {v} — {why}"]

    ns = results.get("no_selection") or {}
    if ns:
        lines += [
            "",
            "CONTROL — SAME MACHINERY, RANKING REMOVED (hold EVERY",
            "eligible name, equal weight). The universe is 22 tickers",
            "chosen in 2026 and includes several of the era's largest",
            "winners, so ranking inside it looks good whether or not",
            "ranking adds anything. This row is the only way to tell",
            "'momentum selection works' from 'these 22 stocks went up':",
            f"  train  {_fmt(ns.get('train'))}",
            f"  test   {_fmt(ns.get('test'))}",
            "  If the arms above do not clearly beat THIS, the ranking is",
            "  decoration and the universe is the result.",
        ]
    el = results.get("eligible") or {}
    if el.get("train") or el.get("test"):
        lines.append("")
        lines.append("ELIGIBLE NAMES PER REBALANCE — 'top N of the "
                     "universe' means nothing if only N qualified:")
        for label in ("train", "test"):
            e = el.get(label) or {}
            if e:
                lines.append(f"  {label:<6} mean {e['mean']:.1f}  "
                             f"range {e['min']}-{e['max']}  "
                             f"months fully in cash: {e['empty_months']}")

    lines += [
        "",
        "READING A FAILURE CORRECTLY (recorded before the run): the",
        "published effect is strongest in the LONG-SHORT spread, and the",
        "short leg is prohibited (§87). A long-only version keeps market",
        "beta and drops half the factor, so failure here means 'not",
        "capturable long-only in 21 names', NOT 'the factor is false'.",
        "",
        "COST NOTE: names carried across a rebalance pay nothing; only",
        "entries and exits are charged. Equal-weight drift is not",
        "re-charged, so these figures are slightly OPTIMISTIC on cost —",
        "read them next to the turnover column.",
        "",
        "EVEN IF CONFIRMED: this is a portfolio strategy needing 3-5",
        "simultaneous positions rebalanced monthly. It does not modify",
        "RS-02, would not replace it, and needs its own adoption",
        "decision. LAW 12/20 — nothing here is adopted.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data. Run: python -m mve.backfill --years 20")
    from .report import save_and_print
    save_and_print("cross_sectional", summary(run_h22(store)))
