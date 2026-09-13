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


# The H-26 cohort (registered 2026-09-12 in docs/PREREGISTERED.md,
# BEFORE this set existed). Ten names filling six clusters the universe
# has never held, selected on STRUCTURE — options depth, cluster
# coverage, price structure able to carry a doctrine contract — and
# explicitly NOT on the analyst ratings that prompted the question.
#
# These are NOT tradeable. They are a fetch/study set and nothing else
# until the registered walk-forward returns CONFIRMED and the operator
# adopts (all ten or none). H-23's CANDIDATE_UNIVERSE above is left
# frozen for that study's reproducibility — this is a separate set, not
# an edit of it.
H26_CANDIDATE_UNIVERSE = {
    "FCX":  "materials",        # copper
    "NEM":  "materials",        # gold — grouped with FCX deliberately:
                                # different drivers, but the cluster cap
                                # is a risk control and the tighter
                                # reading is the safe one (registration)
    "CCJ":  "energy",           # uranium; GICS Energy, 3rd in cluster
    "NEE":  "utilities",
    "SO":   "utilities",
    "DHI":  "homebuilders",
    "LEN":  "homebuilders",
    "UNP":  "rail",             # a railroad is neither the aerospace
                                # pair (BA/RTX) nor the airlines
    "PLD":  "real_estate",
    "ISRG": "health_devices",   # device/robotics, not insurer (UNH) or
                                # pharma (ABBV/PFE) — the argument JNJ
                                # lacked at H-23. Stated risk: a 4th
                                # healthcare name widens that exposure.
}

# Sector benchmarks for the H-26 cohort. XLB, XLU and XLRE are new to
# this program and must be fetched for the study. CCJ->XLE is recorded
# in the registration as an imperfect benchmark (a uranium miner does
# not track oil) rather than solved by inventing one.
H26_CANDIDATE_SECTOR_ETF = {
    "FCX": "XLB", "NEM": "XLB",
    "CCJ": "XLE",
    "NEE": "XLU", "SO": "XLU",
    "DHI": "XLY", "LEN": "XLY",
    "UNP": "XLI",
    "PLD": "XLRE",
    "ISRG": "XLV",
}


# All bar series a full scan needs: universe + benchmark + sector ETFs.
def required_tickers() -> list:
    return sorted(set(UNIVERSE) | {BENCHMARK} | set(SECTOR_ETF.values()))


# All bar series the H-23 expansion study needs — incumbents AND
# candidates from one pull, so the two arms are never on mixed data.
def expansion_required_tickers() -> list:
    return sorted(set(required_tickers()) | set(CANDIDATE_UNIVERSE)
                  | set(CANDIDATE_SECTOR_ETF.values()))


# All bar series the H-26 study needs — the live universe AND the
# H-26 candidates from ONE pull, so the two arms are never on mixed
# data (LAW 18). H-23's candidates are already inside UNIVERSE since
# adoption, so they arrive via required_tickers().
def h26_required_tickers() -> list:
    return sorted(set(required_tickers()) | set(H26_CANDIDATE_UNIVERSE)
                  | set(H26_CANDIDATE_SECTOR_ETF.values()))
