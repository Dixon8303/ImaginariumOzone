"""Markov regime matrix, measured against the null it needs (H23, §72).

An outside dossier proposes the classical hedge-fund construction: label
every day Bull / Sideways / Bear by its trailing 20-day return (+/-5%),
tally the 3x3 transition matrix, and read the diagonal as evidence that
regimes are "sticky". Its signal is P(Bull tomorrow) - P(Bear tomorrow).

The construction is real and the stationary-distribution caveat it
raises is honest. But the dossier reads its own diagonal as a finding,
and that step does not survive a control:

**Consecutive states share 19 of their 20 bars.** Today's window and
tomorrow's differ by one dropped bar and one added bar, so the state
label is autocorrelated BY CONSTRUCTION, before any market behaviour is
involved. A pure IID random walk — no regimes, nothing to detect —
produces roughly 86% stickiness under exactly this definition. Any real
matrix must therefore be compared against a shuffled null, or the
diagonal is measuring the window, not the market.

`shuffled_null` does that: it shuffles DAILY returns (destroying every
scrap of serial structure while preserving the return distribution),
rebuilds the rolling windows, and re-labels. Whatever persistence
survives in the real matrix ABOVE that null is the only part that could
carry information.

The second correction is sample size. A 5,000-bar history looks like
5,000 observations and is not: with a 20-day window there are about
n/20 non-overlapping samples. Precision quoted on the raw count is
roughly 4.5x too confident.

This module DIAGNOSES the method. It does not trade it. A trading use
is pre-registered separately, and only becomes worth registering if the
excess persistence below is non-trivial.

    python -m mve.markov
"""
from __future__ import annotations

import random

from .backtest import DATA_ROOT
from .store import DataStore
from .universe import BENCHMARK

LOOKBACK = 20             # dossier's definition, kept verbatim
THRESHOLD = 0.05          # +/-5% — the dossier's arbitrary cut, kept as-is
SEED = 20260823
NULL_TRIALS = 200
STATES = (1, 0, -1)
LABELS = {1: "Bull", 0: "Sideways", -1: "Bear"}


def label_states(closes: list, lookback: int = LOOKBACK,
                 threshold: float = THRESHOLD) -> list:
    """Trailing-return state per bar, exactly as the dossier defines it."""
    out = []
    for i in range(lookback, len(closes)):
        prior = closes[i - lookback]
        if not prior:
            continue
        r = closes[i] / prior - 1.0
        out.append(1 if r >= threshold else (-1 if r <= -threshold else 0))
    return out


def transition_matrix(states: list) -> dict:
    """{from_state: {to_state: probability}}. Rows sum to 1."""
    counts = {a: {b: 0 for b in STATES} for a in STATES}
    for a, b in zip(states, states[1:]):
        counts[a][b] += 1
    matrix = {}
    for a in STATES:
        total = sum(counts[a].values())
        matrix[a] = ({b: counts[a][b] / total for b in STATES} if total
                     else {b: 0.0 for b in STATES})
    return matrix


def stickiness(states: list) -> float:
    """Share of days where the state does not change — the diagonal the
    dossier reads as regime persistence."""
    pairs = list(zip(states, states[1:]))
    return (sum(1 for a, b in pairs if a == b) / len(pairs)) if pairs else 0.0


def daily_returns(closes: list) -> list:
    return [closes[i] / closes[i - 1] - 1.0
            for i in range(1, len(closes)) if closes[i - 1]]


def shuffled_null(closes: list, trials: int = NULL_TRIALS,
                  seed: int = SEED, lookback: int = LOOKBACK,
                  threshold: float = THRESHOLD) -> dict:
    """Stickiness of the SAME return distribution with all serial
    structure destroyed. This is the number the dossier's diagonal has
    to beat to mean anything."""
    rets = daily_returns(closes)
    if len(rets) < lookback * 3:
        return {}
    rng = random.Random(seed)
    values = []
    for _ in range(trials):
        shuffled = rets[:]
        rng.shuffle(shuffled)
        px, series = 100.0, [100.0]
        for r in shuffled:
            px *= (1.0 + r)
            series.append(px)
        values.append(stickiness(label_states(series, lookback, threshold)))
    values.sort()
    return {"trials": trials,
            "mean": sum(values) / len(values),
            "p05": values[int(len(values) * 0.05)],
            "p95": values[min(len(values) - 1, int(len(values) * 0.95))]}


def stationary(matrix: dict, steps: int = 500) -> dict:
    """Long-run state mix — where multi-step forecasts converge and, as
    the dossier correctly notes, directional edge goes to zero."""
    dist = {s: 1.0 / len(STATES) for s in STATES}
    for _ in range(steps):
        nxt = {s: 0.0 for s in STATES}
        for a in STATES:
            for b in STATES:
                nxt[b] += dist[a] * matrix[a][b]
        dist = nxt
    return dist


def signal_strength(matrix: dict, state: int) -> float:
    """The dossier's formula: P(Bull next) - P(Bear next). Long-only
    here — the short leg it prescribes is prohibited (§87)."""
    row = matrix.get(state, {})
    return row.get(1, 0.0) - row.get(-1, 0.0)


def analyse(closes: list, ticker: str) -> dict:
    states = label_states(closes)
    if len(states) < LOOKBACK * 3:
        return {}
    matrix = transition_matrix(states)
    real = stickiness(states)
    null = shuffled_null(closes)
    return {
        "ticker": ticker,
        "bars": len(states),
        "independent_windows": len(states) // LOOKBACK,
        "matrix": matrix,
        "stickiness": real,
        "null": null,
        "excess": (real - null["mean"]) if null else None,
        "beats_null": (real > null["p95"]) if null else None,
        "stationary": stationary(matrix),
        "signal": {s: signal_strength(matrix, s) for s in STATES},
    }


def summary(results: list) -> str:
    lines = [
        "MARKOV REGIME MATRIX — measured against its null (H23, §72)",
        f"states by trailing {LOOKBACK}-day return, +/-{THRESHOLD:.0%} "
        "(the dossier's definition, kept verbatim)",
        "",
        "WHY THE NULL IS THE WHOLE POINT: consecutive states share 19 of",
        "their 20 bars, so the label is autocorrelated BEFORE any market",
        "behaviour is involved. A pure random walk scores ~86% stickiness",
        "under this definition. Only persistence ABOVE the shuffled null",
        "could carry information.",
        "",
        f"  {'ticker':<8}{'stickiness':>12}{'null mean':>11}{'null p95':>10}"
        f"{'excess':>9}  verdict",
    ]
    beat = 0
    for r in results:
        if not r or not r.get("null"):
            continue
        n = r["null"]
        verdict = "ABOVE NULL" if r["beats_null"] else "indistinguishable"
        beat += 1 if r["beats_null"] else 0
        lines.append(f"  {r['ticker']:<8}{r['stickiness']:>11.1%}"
                     f"{n['mean']:>11.1%}{n['p95']:>10.1%}"
                     f"{r['excess']:>+9.1%}  {verdict}")

    judged = [r for r in results if r and r.get("null")]
    if judged:
        lines += ["",
                  f"  {beat}/{len(judged)} tickers show stickiness above the "
                  "95th percentile of their own shuffled null.",
                  "  At a 5% false-positive rate, "
                  f"~{len(judged) * 0.05:.1f} would clear it by chance."]
        r0 = judged[0]
        lines += ["",
                  "SAMPLE SIZE, corrected: "
                  f"{r0['bars']:,} bars looks like {r0['bars']:,} "
                  f"observations but is about "
                  f"{r0['independent_windows']:,} non-overlapping windows. "
                  "Any precision quoted on the raw bar count is roughly "
                  f"{LOOKBACK ** 0.5:.1f}x too confident."]

        lines += ["", "TRANSITION MATRIX + SIGNAL — first ticker shown:"]
        m = r0["matrix"]
        header = "from / to"
        lines.append(f"  {header:<12}" +
                     "".join(f"{LABELS[b]:>11}" for b in STATES))
        for a in STATES:
            lines.append(f"  {LABELS[a]:<12}" +
                         "".join(f"{m[a][b]:>11.1%}" for b in STATES))
        lines.append("  signal P(Bull)-P(Bear) by current state: " +
                     ", ".join(f"{LABELS[s]} {r0['signal'][s]:+.2f}"
                               for s in STATES))
        st = r0["stationary"]
        lines.append("  stationary mix: " +
                     ", ".join(f"{LABELS[s]} {st[s]:.1%}" for s in STATES)
                     + " — where multi-step forecasts converge and "
                     "directional edge is zero, as the dossier notes.")

    lines += ["",
              "WHAT THIS DOES NOT DO: it does not trade. Whether the signal",
              "improves RS-02 is a separate question, and one not worth",
              "pre-registering unless the excess above is non-trivial —",
              "a filter built on a matrix that only measures its own",
              "window would be noise with extra steps.",
              "",
              "LAW 12/20: nothing here is adopted. The short leg the",
              "dossier prescribes is prohibited regardless (§87, long",
              "premium only), so only the long side could ever apply."]
    return "\n".join(lines)


if __name__ == "__main__":
    store = DataStore(DATA_ROOT)
    tickers = store.tickers()
    if not tickers:
        raise SystemExit("No data. Run: python -m mve.backfill --years 20")
    out = []
    for t in [BENCHMARK] + [x for x in sorted(tickers) if x != BENCHMARK][:7]:
        bars = store.bars(t)
        if bars is None or bars.empty:
            continue
        out.append(analyse([float(c) for c in bars["close"]], t))
    from .report import save_and_print
    save_and_print("markov", summary(out))
