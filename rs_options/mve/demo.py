#!/usr/bin/env python3
"""MVE demo: synthetic universe → ingest → canary-first research session.

Run from rs_options/:  python -m mve.demo
Writes data + telemetry under a temp directory and prints the session
summary plus the §63 rejection-forensics aggregate.
"""
from __future__ import annotations

import tempfile
from datetime import date

from mve.session import run_research_session
from mve.store import DataStore
from mve.telemetry import TelemetryLog
from mve.vendors import SyntheticVendor

AS_OF = "2026-07-01"   # a date where RS-01 fires on the synthetic path
START = date(2026, 3, 2)


def seed(store: DataStore) -> None:
    v = SyntheticVendor(start=START, days=115)
    # Benchmark drifts slightly down late; RUNR outruns it; LAGG lags.
    store.ingest_bars(v.bars("SPY", base=500.0, drift=0.0002, amp=0.015))
    store.ingest_bars(v.bars("XLK", base=200.0, drift=0.0004, amp=0.015, phase=0.5))
    store.ingest_bars(v.bars("RUNR", base=80.0, drift=0.0035, amp=0.01, phase=1.0))
    store.ingest_bars(v.bars("LAGG", base=60.0, drift=-0.0010, amp=0.02, phase=2.0))

    for ticker in ("RUNR", "LAGG"):
        spot = float(store.bars(ticker, end=AS_OF)["close"].iloc[-1])
        store.ingest_chains(v.chain(ticker, AS_OF, spot))


def main() -> None:
    root = tempfile.mkdtemp(prefix="mve_demo_")
    store = DataStore(f"{root}/parquet")
    telemetry = TelemetryLog(f"{root}/telemetry.jsonl")
    seed(store)

    result = run_research_session(
        store, universe=["RUNR", "LAGG"], as_of=AS_OF, telemetry=telemetry,
        benchmark="SPY", sector_map={"RUNR": "XLK", "LAGG": "XLK"},
    )

    print(f"Session {result.as_of} — canary: {'PASS' if result.canary_ok else 'FAIL'}")
    print(f"scanned={result.scanned} candidates={result.candidates} "
          f"authorized={result.authorized} rejected={result.rejected}")
    for ticker, setup, status in result.decisions:
        print(f"  {ticker:<6} {setup:<6} -> {status}")
    forensics = telemetry.rejection_summary()
    if forensics:
        print("Rejection forensics (gate -> count):")
        for reason, count in forensics.items():
            print(f"  {reason}: {count}")
    print(f"telemetry: {telemetry.path}")


if __name__ == "__main__":
    main()
