"""Research session runner (spec §61, §81, §87).

Order of operations, non-negotiable:
  1. Canary suite through the live gate stack — any authorization is a
     Level 0 halt and the session never scans (§61).
  2. Macro state from the static calendar (§11-§12).
  3. Per ticker: point-in-time bars → RS features → RS-01/RS-02 detectors
     → chain selection → TradeCandidate → RiskEngine.evaluate.
  4. Every evaluation (authorized or rejected) → telemetry JSONL with
     Gate_Margins forensics (§62-§63).

RESEARCH/PAPER modes only. There is no order transmission path in the MVE.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from rs_options_risk import (AccountState, AccountType, Mode, RiskEngine,
                             TradeCandidate, UnderlyingContext,
                             run_canary_suite)

from .chain_select import select_call
from .macro_calendar import load_calendar, macro_state
from .rs_features import compute_features
from .setups import detect_all
from .store import DataStore
from .telemetry import TelemetryLog

EXPECTED_HOLD_MINUTES = 780.0     # ~2 trading days at 6.5h — CALIBRATE
NOTIONAL_EQUITY = 100_000.0       # research-mode notional account


class CanaryFailure(RuntimeError):
    """§61: a must-reject candidate was authorized — Level 0 halt."""


@dataclass
class SessionResult:
    as_of: str
    canary_ok: bool
    scanned: int = 0
    candidates: int = 0
    authorized: int = 0
    rejected: int = 0
    decisions: list = field(default_factory=list)


def run_research_session(store: DataStore, universe: list, as_of: str,
                         telemetry: TelemetryLog,
                         benchmark: str = "SPY",
                         sector_map: dict | None = None,
                         macro_csv: str | None = None,
                         mode: Mode = Mode.RESEARCH,
                         engine: RiskEngine | None = None) -> SessionResult:
    if mode not in (Mode.RESEARCH, Mode.PAPER):
        raise ValueError("MVE runs RESEARCH or PAPER only — no live modes (§87)")

    engine = engine or RiskEngine()
    today = date.fromisoformat(as_of)
    sector_map = sector_map or {}

    # ── 1. prove the brakes work (§61) ─────────────────────────────────
    report = run_canary_suite(engine, today, mode=mode)
    telemetry.write({"type": "canary", "as_of": as_of, "ok": report.ok,
                     "results": [(r.name, r.status, r.ok) for r in report.results]})
    if not report.ok:
        raise CanaryFailure("LEVEL 0 HALT — canary suite failed:\n" + report.summary())

    # ── 2. macro state ─────────────────────────────────────────────────
    macro = None
    if macro_csv:
        now = datetime.combine(today, datetime.min.time(),
                               tzinfo=timezone.utc).replace(hour=15)  # mid-session UTC
        macro = macro_state(load_calendar(macro_csv), now)

    bench_bars = store.bars(benchmark, end=as_of)
    result = SessionResult(as_of=as_of, canary_ok=True)

    account = AccountState(
        equity=NOTIONAL_EQUITY, start_of_day_equity=NOTIONAL_EQUITY,
        peak_equity=NOTIONAL_EQUITY, account_type=AccountType.MARGIN,
        buying_power=2 * NOTIONAL_EQUITY,
    )

    # ── 3. scan ────────────────────────────────────────────────────────
    for ticker in universe:
        if ticker == benchmark:
            continue
        bars = store.bars(ticker, end=as_of)          # point-in-time (§49)
        if len(bars) < 30 or len(bench_bars) < 30:
            continue
        result.scanned += 1

        sector_ticker = sector_map.get(ticker)
        sector_bars = store.bars(sector_ticker, end=as_of) if sector_ticker else None
        features = compute_features(bars, bench_bars, sector_bars)

        for hit in detect_all(bars, features):
            result.candidates += 1
            option = select_call(store.chain(ticker, as_of), as_of)
            record = {"type": "evaluation", "as_of": as_of, "ticker": ticker,
                      "setup": hit["setup_id"], "rationale": hit["rationale"],
                      "features": {k: v for k, v in features.items()}}

            if option is None:
                record["decision"] = {"Decision": {"Status": "REJECT",
                                                   "Reasons": ["OPTION_INVALID"],
                                                   "Mode": mode.value}}
                result.rejected += 1
                telemetry.write(record)
                continue

            candidate = TradeCandidate(
                underlying=UnderlyingContext(
                    ticker=ticker, price=hit["close"],
                    cluster=sector_map.get(ticker, "")),
                option=option,
                setup_id=hit["setup_id"],
                invalidation_price=hit["invalidation_price"],
                expected_hold_minutes=EXPECTED_HOLD_MINUTES,
                trade_date=today,
                opportunity_score=hit["opportunity_score"],
                is_day_trade=False,
                holds_overnight=True,
            )
            if macro is not None:
                candidate.macro = macro

            decision = engine.evaluate(candidate, account, mode=mode)
            record["decision"] = decision.to_telemetry()
            telemetry.write(record)
            result.decisions.append((ticker, hit["setup_id"], decision.status.value))
            if decision.authorized:
                result.authorized += 1
            else:
                result.rejected += 1

    telemetry.write({"type": "session_summary", "as_of": as_of,
                     "scanned": result.scanned, "candidates": result.candidates,
                     "authorized": result.authorized, "rejected": result.rejected})
    return result
