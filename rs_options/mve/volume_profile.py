"""Volume-by-price — overhead supply (H11, spec §72).

Classical support/resistance asks where price TURNED. Volume-by-price
asks where shares actually CHANGED HANDS, which is a different and more
mechanical question: every share bought above the current price is a
holder sitting on a loss, and those holders are the supply a rally has
to absorb on the way up.

The measurement here is OVERHEAD SUPPLY — the share of the trailing
window's volume that traded ABOVE today's close. Low overhead supply
means clear air above; high means the move is climbing into a wall of
break-even sellers.

Why it is worth testing when H1 (52-week high) and H3 (anchored VWAP)
both failed: those are PRICE levels, and RS-02's 20-day breakout already
encodes price structure. This is a VOLUME measurement — genuinely new
information rather than a restatement of the entry rule.

No new data source: computed from the daily bars already on disk.
"""
from __future__ import annotations

import pandas as pd

PROFILE_WINDOW = 60         # trailing sessions in the profile (CALIBRATE)
PRICE_BINS = 50             # resolution of the price axis (CALIBRATE)
MIN_PROFILE_BARS = 30       # below this the profile is too sparse to read


def volume_by_price(bars: pd.DataFrame, window: int = PROFILE_WINDOW,
                    bins: int = PRICE_BINS) -> pd.DataFrame | None:
    """Distribute each session's volume across its own high-low range,
    then sum into price bins. Returns (price_low, price_high, volume) or
    None when there is not enough history.

    Spreading volume across the bar's range — rather than dumping it all
    at the close — is the honest approximation available from daily
    data: we know the shares traded somewhere inside that range, and
    nothing finer without intraday prints.
    """
    if bars is None or len(bars) < MIN_PROFILE_BARS:
        return None
    recent = bars.iloc[-window:]
    lo = float(recent["low"].min())
    hi = float(recent["high"].max())
    if not hi > lo:
        return None
    edges = pd.Series(range(bins + 1)) / bins * (hi - lo) + lo
    totals = [0.0] * bins
    for _, bar in recent.iterrows():
        b_lo, b_hi = float(bar["low"]), float(bar["high"])
        vol = float(bar.get("volume", 0.0) or 0.0)
        if vol <= 0:
            continue
        if b_hi <= b_lo:                       # zero-range bar: single bin
            idx = min(int((b_lo - lo) / (hi - lo) * bins), bins - 1)
            totals[idx] += vol
            continue
        # volume spread uniformly over the bins the bar's range covers
        first = min(int((b_lo - lo) / (hi - lo) * bins), bins - 1)
        last = min(int((b_hi - lo) / (hi - lo) * bins), bins - 1)
        share = vol / (last - first + 1)
        for i in range(first, last + 1):
            totals[i] += share
    return pd.DataFrame({"price_low": edges[:-1].values,
                         "price_high": edges[1:].values,
                         "volume": totals})


def overhead_supply(bars: pd.DataFrame, window: int = PROFILE_WINDOW,
                    bins: int = PRICE_BINS) -> float | None:
    """Fraction of the window's volume that traded ABOVE today's close.
    None when the profile cannot be built (callers fail closed)."""
    profile = volume_by_price(bars, window, bins)
    if profile is None:
        return None
    total = float(profile["volume"].sum())
    if total <= 0:
        return None
    close = float(bars["close"].iloc[-1])
    # a bin counts as overhead in proportion to how much of it sits above
    above = 0.0
    for _, row in profile.iterrows():
        lo, hi, vol = row["price_low"], row["price_high"], row["volume"]
        if close >= hi:
            continue
        if close <= lo:
            above += vol
        else:
            above += vol * (hi - close) / (hi - lo)
    return above / total


def point_of_control(bars: pd.DataFrame, window: int = PROFILE_WINDOW,
                     bins: int = PRICE_BINS) -> float | None:
    """Midpoint of the heaviest-volume bin — the price level where the
    most shares changed hands. Reported for context, not filtered on."""
    profile = volume_by_price(bars, window, bins)
    if profile is None or profile["volume"].sum() <= 0:
        return None
    row = profile.loc[profile["volume"].idxmax()]
    return float((row["price_low"] + row["price_high"]) / 2.0)


def clear_overhead(bars: pd.DataFrame, max_share: float) -> bool:
    """H11 filter: overhead supply below `max_share`. Fail-closed — an
    unbuildable profile blocks rather than assuming clear air."""
    share = overhead_supply(bars)
    return share is not None and share < max_share
