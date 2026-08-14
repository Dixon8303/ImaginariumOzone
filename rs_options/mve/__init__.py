"""mve — Minimum Viable Engine (spec v2.2 §87).

The reduced build of Phases 1-3 for a single operator: vendor EOD/daily
data in DuckDB + partitioned Parquet, a static macro calendar, hierarchical
RS features, the two baseline setups (RS-01, RS-02), and a research session
runner that goes canary-first through the rs_options_risk gate stack.

No trading. Research and Paper phases only (§88 Phases 1-5).
Every threshold marked CALIBRATE is a research placeholder (LAW 12).
"""

__version__ = "0.1.0"
