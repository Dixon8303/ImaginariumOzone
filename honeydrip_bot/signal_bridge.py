"""
AAPL Stabilized Pro — adapted from the operator's PineScript strategy.

Entry:  EMA(9) crosses over EMA(21), ADX(14) > 20, not a Friday.
Exit:   4.5% defensive stop; stop to breakeven at +3%; 3% trail at +6%; 20% target.

get_signals() produces entry signals from daily bars.
evaluate_exit() is a pure function for managing an open position — the engine
or Claude (via Robinhood MCP) calls it with current position state.
"""

import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import pandas as pd

TICKER = "AAPL"
EMA_FAST_LEN = 9
EMA_SLOW_LEN = 21
ADX_LEN = 14
ADX_THRESHOLD = 20

TARGET_PCT = 0.20          # take profit at +20%
MAX_LOSS_PCT = 0.045       # tight defensive stop at -4.5%
BREAKEVEN_TRIGGER = 0.03   # move stop to breakeven at +3%
TRAIL_TRIGGER = 0.06       # start trailing at +6%
TRAIL_PCT = 0.03           # trail distance 3%


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _wilder(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1 / length, adjust=False).mean()


def compute_adx(df: pd.DataFrame, length: int = ADX_LEN) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0)) * up.clip(lower=0)
    minus_dm = ((down > up) & (down > 0)) * down.clip(lower=0)
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr = _wilder(tr, length)
    plus_di = 100 * _wilder(plus_dm, length) / atr
    minus_di = 100 * _wilder(minus_dm, length) / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return _wilder(dx, length)


def check_entry(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    df: daily OHLC bars, oldest first, columns: open/high/low/close.
    Returns a signal dict if the latest bar triggers an entry, else None.
    """
    if len(df) < EMA_SLOW_LEN + ADX_LEN:
        return None

    ema_fast = _ema(df["close"], EMA_FAST_LEN)
    ema_slow = _ema(df["close"], EMA_SLOW_LEN)
    adx = compute_adx(df)

    crossed = (
        ema_fast.iloc[-1] > ema_slow.iloc[-1]
        and ema_fast.iloc[-2] <= ema_slow.iloc[-2]
    )
    trending = adx.iloc[-1] > ADX_THRESHOLD
    # PineScript: dayofweek != friday — avoid weekend gap risk
    not_friday = datetime.now(timezone.utc).weekday() != 4

    if not (crossed and trending and not_friday):
        return None

    price = float(df["close"].iloc[-1])
    return {
        "ticker": TICKER,
        "action": "buy",
        "price": price,
        "confidence": min(0.95, 0.60 + (float(adx.iloc[-1]) - ADX_THRESHOLD) / 100),
        "rationale": (
            f"EMA{EMA_FAST_LEN}/{EMA_SLOW_LEN} crossover with ADX "
            f"{adx.iloc[-1]:.1f} > {ADX_THRESHOLD}, non-Friday session"
        ),
        "source": "aapl_stabilized_pro",
        "exit_plan": {
            "target_price": round(price * (1 + TARGET_PCT), 2),
            "initial_stop": round(price * (1 - MAX_LOSS_PCT), 2),
            "breakeven_at": round(price * (1 + BREAKEVEN_TRIGGER), 2),
            "trail_at": round(price * (1 + TRAIL_TRIGGER), 2),
            "trail_pct": TRAIL_PCT,
        },
    }


def evaluate_exit(
    entry_price: float,
    current_close: float,
    highest_high_since_entry: float,
) -> Dict[str, Any]:
    """
    Pure exit-management function — mirrors the PineScript management block.
    Call on every check of an open position.
    """
    peak_profit = (highest_high_since_entry - entry_price) / entry_price

    stop_price = entry_price * (1 - MAX_LOSS_PCT)
    if peak_profit >= BREAKEVEN_TRIGGER:
        stop_price = entry_price
    if peak_profit >= TRAIL_TRIGGER:
        stop_price = max(stop_price, current_close * (1 - TRAIL_PCT))

    if current_close >= entry_price * (1 + TARGET_PCT):
        return {"exit": True, "reason": "20% target reached", "stop_price": round(stop_price, 2)}
    if current_close <= stop_price:
        return {"exit": True, "reason": "defensive stop hit", "stop_price": round(stop_price, 2)}
    return {"exit": False, "reason": "hold", "stop_price": round(stop_price, 2)}


def _fetch_bars_alpaca(ticker: str, limit: int = 100) -> Optional[pd.DataFrame]:
    """Fetch daily bars from Alpaca data API. Requires paper credentials."""
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        return None
    try:
        import alpaca_trade_api as tradeapi
        from honeydrip_bot.config import ALPACA_BASE_URL
        api = tradeapi.REST(key, secret, base_url=ALPACA_BASE_URL)
        bars = api.get_bars(ticker, "1Day", limit=limit).df
        if bars.empty:
            return None
        return bars[["open", "high", "low", "close"]]
    except Exception as e:
        print(f"Bar fetch failed: {e}")
        return None


def get_signals() -> List[Dict[str, Any]]:
    df = _fetch_bars_alpaca(TICKER)
    if df is None:
        print(
            "No bar data available (Alpaca data credentials not set or fetch failed). "
            "In live MCP mode, Claude can fetch quotes via Robinhood MCP and call "
            "check_entry() with a bars DataFrame directly."
        )
        return []
    signal = check_entry(df)
    return [signal] if signal else []
