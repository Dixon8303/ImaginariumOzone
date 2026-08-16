"""Underlying-signal backtester for RS-01/RS-02 (spec §44, §47, §57).

Walks history day by day with point-in-time information only (§49):
features are computed from bars up to the signal day, entries fill at the
NEXT day's open, exits are evaluated bar by bar with conservative fills.

What this validates: the RS setup signal on the UNDERLYING, in R-multiples.
What it cannot validate: options P&L (needs historical chains — paid data),
slippage/fees on contracts, IV behavior. Results here are a necessary
first hurdle, not a green light (LAW 19, LAW 20).

Exit model (CALIBRATE — these are the §41 research hypotheses):
  stop   invalidation price; gap-through fills at the open (worse than 1R)
  target +2R; if stop and target are both touched in one bar, STOP WINS
  time   close out at the close after MAX_HOLD_BARS
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

from .rs_features import compute_features
from .setups import detect_all
from .store import DataStore
from .universe import BENCHMARK, SECTOR_ETF, UNIVERSE

# Exit doctrine per the 2026-08-15 exit-policy study (150 real signals):
# "wide" won on TRAIN (+0.384R vs baseline +0.295R) and CONFIRMED on TEST
# (+0.181R vs baseline +0.026R). ATR-trail scored best on test but was not
# the train winner — watch-list only, per the pre-registered discipline.
TARGET_R = 3.0          # CALIBRATE — study-selected
MAX_HOLD_BARS = 15      # CALIBRATE — study-selected
MIN_HISTORY = 60        # bars required before a ticker is eligible
DATA_ROOT = "data/parquet"


@dataclass
class Position:
    ticker: str
    setup: str
    signal_date: str
    entry_date: str
    entry: float
    stop: float
    target: float
    r_denom: float
    bars_held: int = 0


@dataclass
class Trade:
    ticker: str
    setup: str
    entry_date: str
    exit_date: str
    entry: float
    exit: float
    r_multiple: float
    exit_reason: str
    bars_held: int


@dataclass
class BacktestResult:
    trades: list = field(default_factory=list)
    skipped_signals: int = 0
    filtered_signals: int = 0      # rejected by an entry_filter (no silent caps)

    def per_setup(self) -> dict:
        out = {}
        for setup in sorted({t.setup for t in self.trades}):
            rs = [t.r_multiple for t in self.trades if t.setup == setup]
            wins = [r for r in rs if r > 0]
            out[setup] = {
                "trades": len(rs),
                "win_rate": round(len(wins) / len(rs), 3) if rs else 0.0,
                "avg_win_r": round(sum(wins) / len(wins), 3) if wins else 0.0,
                "avg_loss_r": round(sum(r for r in rs if r <= 0)
                                    / max(1, len(rs) - len(wins)), 3),
                "expectancy_r": round(sum(rs) / len(rs), 3) if rs else 0.0,
                "max_drawdown_r": round(_max_drawdown(rs), 3),
                "avg_hold_bars": round(sum(t.bars_held for t in self.trades
                                           if t.setup == setup) / len(rs), 1),
            }
        return out

    def summary(self) -> str:
        lines = ["BACKTEST — RS setups on the UNDERLYING (options P&L NOT modeled)",
                 f"trades: {len(self.trades)}   signals skipped (no valid R): "
                 f"{self.skipped_signals}", ""]
        for setup, s in self.per_setup().items():
            verdict = ("POSITIVE expectancy" if s["expectancy_r"] > 0
                       else "NEGATIVE expectancy")
            lines += [f"{setup}: {s['trades']} trades | win rate {s['win_rate']:.0%} | "
                      f"avg win +{s['avg_win_r']}R / avg loss {s['avg_loss_r']}R",
                      f"       expectancy {s['expectancy_r']:+}R per trade "
                      f"({verdict}) | max DD {s['max_drawdown_r']}R | "
                      f"avg hold {s['avg_hold_bars']} bars", ""]
        if not self.trades:
            lines.append("No trades triggered — setups never fired on this history.")
        lines.append("Reminder: LAW 19 — winning trades do not prove an edge. "
                     "This is one in-sample pass; walk-forward comes next.")
        return "\n".join(lines)


def _max_drawdown(rs: list) -> float:
    peak = equity = dd = 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        dd = min(dd, equity - peak)
    return dd


def manage_position(pos: Position, bar) -> tuple:
    """One bar of exit logic. Returns (exit_price, reason) or (None, None).
    Conservative ordering: gap-through-stop, then stop, then target, then
    time stop. Stop wins any same-bar tie with the target."""
    if bar["open"] <= pos.stop:
        return float(bar["open"]), "gap_stop"
    if bar["low"] <= pos.stop:
        return pos.stop, "stop"
    if bar["high"] >= pos.target:
        return pos.target, "target"
    if pos.bars_held + 1 >= MAX_HOLD_BARS:
        return float(bar["close"]), "time"
    return None, None


def run_backtest(store: DataStore, universe: list | None = None,
                 benchmark: str = BENCHMARK, sector_map: dict | None = None,
                 start: str | None = None, end: str | None = None,
                 active: tuple = ("RS-01", "RS-02"),
                 entry_filter=None) -> BacktestResult:
    # Research evaluates ALL setups, including disabled ones — that is how
    # a killed setup earns its way back (LAW 20). The live scanner honors
    # setups.ACTIVE_SETUPS instead.
    # entry_filter: optional callable(ticker, bars, bench_slice) -> bool,
    # applied point-in-time at the signal bar (hypothesis studies, §72).
    universe = [t for t in (universe or list(UNIVERSE)) if t != benchmark]
    sector_map = sector_map if sector_map is not None else SECTOR_ETF

    all_bars = {t: store.bars(t) for t in
                set(universe) | {benchmark} | set(sector_map.values())}
    bench = all_bars[benchmark]
    dates = [d for d in bench["trade_date"]
             if (not start or d >= start) and (not end or d <= end)]

    by_date = {t: df.set_index("trade_date") for t, df in all_bars.items()}
    result = BacktestResult()
    open_pos: dict = {}          # ticker -> Position
    pending: list = []           # signals awaiting next-open entry

    for d in dates:
        # ── fill pending entries at today's open ─────────────────────
        still_pending = []
        for sig in pending:
            idx = by_date.get(sig["ticker"])
            if idx is None or d not in idx.index:
                still_pending.append(sig)      # holiday for this ticker
                continue
            entry = float(idx.loc[d, "open"])
            r_denom = entry - sig["invalidation"]
            if r_denom <= 0 or sig["ticker"] in open_pos:
                result.skipped_signals += 1
                continue
            open_pos[sig["ticker"]] = Position(
                ticker=sig["ticker"], setup=sig["setup"],
                signal_date=sig["date"], entry_date=d, entry=entry,
                stop=sig["invalidation"], target=entry + TARGET_R * r_denom,
                r_denom=r_denom)
        pending = still_pending

        # ── manage open positions on today's bar ─────────────────────
        for ticker, pos in list(open_pos.items()):
            idx = by_date[ticker]
            if d not in idx.index or d == pos.entry_date:
                continue
            bar = idx.loc[d]
            exit_price, reason = manage_position(pos, bar)
            pos.bars_held += 1
            if exit_price is not None:
                result.trades.append(Trade(
                    ticker=ticker, setup=pos.setup, entry_date=pos.entry_date,
                    exit_date=d, entry=pos.entry, exit=exit_price,
                    r_multiple=round((exit_price - pos.entry) / pos.r_denom, 3),
                    exit_reason=reason, bars_held=pos.bars_held))
                del open_pos[ticker]

        # ── detect new signals (point-in-time), enter at NEXT open ───
        bench_slice = bench[bench["trade_date"] <= d]
        if len(bench_slice) < MIN_HISTORY:
            continue
        for ticker in universe:
            if ticker in open_pos:
                continue
            df = all_bars.get(ticker)
            if df is None:
                continue
            bars = df[df["trade_date"] <= d]
            if len(bars) < MIN_HISTORY or bars["trade_date"].iloc[-1] != d:
                continue
            sector_ticker = sector_map.get(ticker)
            sector = (all_bars[sector_ticker][all_bars[sector_ticker]["trade_date"] <= d]
                      if sector_ticker in all_bars else None)
            features = compute_features(bars, bench_slice, sector)
            for hit in detect_all(bars, features, active=active):
                if entry_filter is not None and not entry_filter(
                        ticker, bars, bench_slice):
                    result.filtered_signals += 1
                    break
                pending.append({"ticker": ticker, "setup": hit["setup_id"],
                                "invalidation": hit["invalidation_price"],
                                "date": d})
                break                          # one signal per ticker per day

    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    store = DataStore(DATA_ROOT)
    if not store.tickers():
        raise SystemExit("No data found. Run:  python -m mve.backfill")
    res = run_backtest(store, start=args[0] if args else None,
                       end=args[1] if len(args) > 1 else None)
    from .report import save_and_print
    save_and_print("backtest", res.summary())
    with open("data/backtest_results.json", "w") as f:
        json.dump({"per_setup": res.per_setup(),
                   "trades": [vars(t) for t in res.trades]}, f, indent=2)
    print("Full trade list: data/backtest_results.json")
