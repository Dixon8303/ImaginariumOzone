"""DataStore — DuckDB over partitioned Parquet (spec §46, bootstrap tier).

Tables (Tier B/C shapes, daily bootstrap):
  underlying_bars_daily  ticker, trade_date, open, high, low, close, volume
  chains_eod             underlying, trade_date, expiry, strike, right,
                         bid, ask, volume, open_interest, iv, delta

Partitioning: one Parquet file per ticker (bars) / per underlying+date
(chains). Ingest merges with existing rows and dedupes on the natural key,
so backfills are idempotent (§46 "Backfills must be idempotent").
Graduation trigger (§87): move to ClickHouse when backtest queries take
minutes or Tier A intraday snapshots enter scope.
"""
from __future__ import annotations

import os

import duckdb
import pandas as pd

BAR_COLS = ["ticker", "trade_date", "open", "high", "low", "close", "volume"]
CHAIN_COLS = ["underlying", "trade_date", "expiry", "strike", "right",
              "bid", "ask", "volume", "open_interest", "iv", "delta"]


class DataStore:
    def __init__(self, root: str):
        self.root = root
        self._bars_dir = os.path.join(root, "underlying_bars_daily")
        self._chains_dir = os.path.join(root, "chains_eod")
        os.makedirs(self._bars_dir, exist_ok=True)
        os.makedirs(self._chains_dir, exist_ok=True)

    # ------------------------------------------------------------- ingest
    def ingest_bars(self, df: pd.DataFrame) -> int:
        """Idempotent upsert of daily bars; dedupes on (ticker, trade_date)."""
        df = self._validated(df, BAR_COLS, date_cols=["trade_date"])
        written = 0
        for ticker, part in df.groupby("ticker"):
            path = self._bar_path(str(ticker))
            if os.path.exists(path):
                part = pd.concat([pd.read_parquet(path), part])
            part = (part.drop_duplicates(subset=["ticker", "trade_date"], keep="last")
                        .sort_values("trade_date"))
            part.to_parquet(path, index=False)
            written += len(part)
        return written

    def ingest_chains(self, df: pd.DataFrame) -> int:
        """Idempotent upsert of EOD chain snapshots; dedupes on contract key."""
        df = self._validated(df, CHAIN_COLS, date_cols=["trade_date", "expiry"])
        written = 0
        for (und, day), part in df.groupby(["underlying", "trade_date"]):
            path = self._chain_path(str(und), str(day))
            if os.path.exists(path):
                part = pd.concat([pd.read_parquet(path), part])
            part = part.drop_duplicates(
                subset=["underlying", "trade_date", "expiry", "strike", "right"],
                keep="last")
            part.to_parquet(path, index=False)
            written += len(part)
        return written

    # -------------------------------------------------------------- query
    def bars(self, ticker: str, start: str | None = None,
             end: str | None = None) -> pd.DataFrame:
        """Daily bars, oldest first. `end` is inclusive — point-in-time
        reads must pass end=as_of so no future bars leak (§49)."""
        path = self._bar_path(ticker)
        if not os.path.exists(path):
            return pd.DataFrame(columns=BAR_COLS)
        clauses, params = [], []
        if start:
            clauses.append("trade_date >= ?"); params.append(start)
        if end:
            clauses.append("trade_date <= ?"); params.append(end)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return duckdb.execute(
            f"SELECT * FROM read_parquet('{path}') {where} ORDER BY trade_date",
            params).df()

    def chain(self, underlying: str, trade_date: str) -> pd.DataFrame:
        path = self._chain_path(underlying, trade_date)
        if not os.path.exists(path):
            return pd.DataFrame(columns=CHAIN_COLS)
        return duckdb.execute(f"SELECT * FROM read_parquet('{path}')").df()

    def tickers(self) -> list:
        return sorted(f[:-8] for f in os.listdir(self._bars_dir)
                      if f.endswith(".parquet"))

    # ----------------------------------------------------------------- qa
    def bar_gaps(self, ticker: str) -> pd.DataFrame:
        """Calendar-day gaps > 4 days between consecutive bars — feeds the
        Data Integrity Engine's daily QA (§46, §61). Weekends/holidays pass;
        a missing week does not."""
        bars = self.bars(ticker)
        if len(bars) < 2:
            return pd.DataFrame(columns=["prev_date", "next_date", "gap_days"])
        d = pd.to_datetime(bars["trade_date"])
        gap = d.diff().dt.days
        mask = gap > 4
        return pd.DataFrame({
            "prev_date": d.shift()[mask].dt.date.astype(str),
            "next_date": d[mask].dt.date.astype(str),
            "gap_days": gap[mask].astype(int),
        }).reset_index(drop=True)

    # ------------------------------------------------------------ helpers
    def _bar_path(self, ticker: str) -> str:
        return os.path.join(self._bars_dir, f"{ticker}.parquet")

    def _chain_path(self, underlying: str, trade_date: str) -> str:
        d = os.path.join(self._chains_dir, underlying)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{trade_date}.parquet")

    @staticmethod
    def _validated(df: pd.DataFrame, cols: list, date_cols: list) -> pd.DataFrame:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(f"missing columns: {missing}")
        df = df[cols].copy()
        for c in date_cols:
            df[c] = pd.to_datetime(df[c]).dt.date.astype(str)
        return df
