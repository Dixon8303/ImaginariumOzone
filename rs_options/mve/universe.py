"""Trading universe and cluster map (spec §14, §78).

SPY is the benchmark — the RS strategies measure strength *against* it,
so it is not itself a setup candidate. QQQ carries index exposure.
Clusters feed the §78 correlated-exposure caps.
"""
from __future__ import annotations

BENCHMARK = "SPY"

# ticker -> cluster (§78 exposure grouping)
UNIVERSE = {
    "QQQ":  "index",
    "IWM":  "index",
    "NVDA": "semis",
    "AMD":  "semis",
    "AAPL": "megacap_tech",
    "MSFT": "megacap_tech",
    "GOOGL": "megacap_tech",
    "AMZN": "megacap_tech",
    "META": "megacap_tech",
    "NFLX": "media",
    "DIS":  "media",
    "AAL":  "airlines",
    "DAL":  "airlines",
    "JPM":  "financials",
    "BAC":  "financials",
    "XOM":  "energy",
    "WMT":  "consumer",
    "KO":   "consumer",
}

# ticker -> sector benchmark for RS_sector (§14 dynamic benchmark selection)
SECTOR_ETF = {
    "NVDA": "SMH", "AMD": "SMH",
    "AAPL": "XLK", "MSFT": "XLK", "GOOGL": "XLK",
    "AMZN": "XLY", "META": "XLC", "NFLX": "XLC", "DIS": "XLC",
    "AAL": "JETS", "DAL": "JETS",
    "JPM": "XLF", "BAC": "XLF",
    "XOM": "XLE",
    "WMT": "XLP", "KO": "XLP",
}

# All bar series a full scan needs: universe + benchmark + sector ETFs.
def required_tickers() -> list:
    return sorted(set(UNIVERSE) | {BENCHMARK} | set(SECTOR_ETF.values()))
