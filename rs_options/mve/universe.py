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
    "MU":   "semis",
    "AAPL": "megacap_tech",
    "MSFT": "megacap_tech",
    "GOOGL": "megacap_tech",
    "AMZN": "megacap_tech",
    "META": "megacap_tech",
    "PLTR": "software",
    "TSLA": "ev_auto",
    "NFLX": "media",
    "DIS":  "media",
    "AAL":  "airlines",
    "DAL":  "airlines",
    "JPM":  "financials",
    "BAC":  "financials",
    "XOM":  "energy",
    "WMT":  "consumer",
    "KO":   "consumer",
    "SBUX": "consumer",
}
# 2026-08-16 expansion (TSLA, MU, PLTR, SBUX): selected on STRUCTURE —
# deep options liquidity (tight spreads, high OI) and cluster coverage —
# NOT on the operator's per-ticker P&L history, which is small-n noise
# either direction. The strategy-level walk-forward re-run on the
# expanded universe is the arbiter, per the universe-expansion note in
# RESEARCH_LOG. Declined from the same history: SPXW (index options,
# out of §87 scope), VXX (banned ETP), PLUG (price too low for clean
# long-call structures, spreads too wide).

# H-23 expansion candidates (docs/PREREGISTERED.md, registered
# 2026-08-27) — NOT tradeable. These exist only so the expansion study
# and its backfill can target them; nothing in the live scan or paper
# trader reads this set, and none of these names enters UNIVERSE unless
# H-23 confirms (adoption is all-or-none, per the registration).
# Selected on STRUCTURE with live quotes at registration; the rejected
# names and their reasons are frozen in the H-23 entry.
CANDIDATE_UNIVERSE = {
    "UNH":  "healthcare",
    "ABBV": "healthcare",
    "PFE":  "healthcare",
    "BA":   "industrials",
    "RTX":  "industrials",
    "T":    "telecom",
    "VZ":   "telecom",
    "V":    "payments",
    "PYPL": "payments",
    "COIN": "crypto_fin",
    "HOOD": "crypto_fin",
    "SOFI": "financials",
    "ORCL": "software",
    "CRM":  "software",
    "CVX":  "energy",
    "F":    "ev_auto",
}

# ticker -> sector benchmark for RS_sector (§14 dynamic benchmark selection)
SECTOR_ETF = {
    "NVDA": "SMH", "AMD": "SMH", "MU": "SMH",
    "AAPL": "XLK", "MSFT": "XLK", "GOOGL": "XLK", "PLTR": "XLK",
    "AMZN": "XLY", "TSLA": "XLY", "SBUX": "XLY",
    "META": "XLC", "NFLX": "XLC", "DIS": "XLC",
    "AAL": "JETS", "DAL": "JETS",
    "JPM": "XLF", "BAC": "XLF",
    "XOM": "XLE",
    "WMT": "XLP", "KO": "XLP",
}

# Candidate sector benchmarks (H-23) — GICS-aligned: V/PYPL sit in
# financials since the March-2023 GICS reclassification of payment
# processors; COIN and HOOD are classified financials; T/VZ are
# communication services alongside the existing META/NFLX/DIS -> XLC.
CANDIDATE_SECTOR_ETF = {
    "UNH": "XLV", "ABBV": "XLV", "PFE": "XLV",
    "BA": "XLI", "RTX": "XLI",
    "T": "XLC", "VZ": "XLC",
    "V": "XLF", "PYPL": "XLF", "COIN": "XLF", "HOOD": "XLF", "SOFI": "XLF",
    "ORCL": "XLK", "CRM": "XLK",
    "CVX": "XLE",
    "F": "XLY",
}


# All bar series a full scan needs: universe + benchmark + sector ETFs.
def required_tickers() -> list:
    return sorted(set(UNIVERSE) | {BENCHMARK} | set(SECTOR_ETF.values()))


# All bar series the H-23 expansion study needs — incumbents AND
# candidates from one pull, so the two arms are never on mixed data.
def expansion_required_tickers() -> list:
    return sorted(set(required_tickers()) | set(CANDIDATE_UNIVERSE)
                  | set(CANDIDATE_SECTOR_ETF.values()))
