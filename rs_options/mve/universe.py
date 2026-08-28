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
    # H-23 expansion, ADOPTED 2026-08-28 (operator decision, all-or-none
    # per the registration). Selected on structure with live quotes at
    # registration; CONFIRMED by the pre-registered walk-forward:
    # candidates-only +0.135R over 420 OOS trades vs baseline +0.133R
    # (docs/PREREGISTERED.md H-23, docs/reports/expansion_study.txt).
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
# 2026-08-16 expansion (TSLA, MU, PLTR, SBUX): selected on STRUCTURE —
# deep options liquidity (tight spreads, high OI) and cluster coverage —
# NOT on the operator's per-ticker P&L history, which is small-n noise
# either direction. The strategy-level walk-forward re-run on the
# expanded universe is the arbiter, per the universe-expansion note in
# RESEARCH_LOG. Declined from the same history: SPXW (index options,
# out of §87 scope), VXX (banned ETP), PLUG (price too low for clean
# long-call structures, spreads too wide).

# The H-23 cohort (registered 2026-08-27, CONFIRMED and ADOPTED
# 2026-08-28 — the 16 names are now in UNIVERSE above). Kept as a named
# set for study reproducibility and for the tests that pin the cohort;
# `mve.expansion_study` reads it to split cohort-vs-incumbent results.
# Note the study's "baseline" arm meant the pre-adoption 22-name
# UNIVERSE; re-running it post-adoption measures something different.
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
    # H-23 adoption (2026-08-28): GICS-aligned — V/PYPL are financials
    # since the March-2023 payment-processor reclassification; COIN,
    # HOOD, SOFI likewise; T/VZ are communication services beside
    # META/NFLX/DIS.
    "UNH": "XLV", "ABBV": "XLV", "PFE": "XLV",
    "BA": "XLI", "RTX": "XLI",
    "T": "XLC", "VZ": "XLC",
    "V": "XLF", "PYPL": "XLF", "COIN": "XLF", "HOOD": "XLF", "SOFI": "XLF",
    "ORCL": "XLK", "CRM": "XLK",
    "CVX": "XLE",
    "F": "XLY",
}

# The H-23 cohort's sector benchmarks — now duplicated into SECTOR_ETF
# above by the 2026-08-28 adoption; kept, like CANDIDATE_UNIVERSE, for
# study reproducibility and the cohort-pinning tests.
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
