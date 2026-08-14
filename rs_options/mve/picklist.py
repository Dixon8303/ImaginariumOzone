"""Pick list — the autonomous-selection output (spec §80 OPPORTUNITIES).

Consumes a session's telemetry records and produces the ranked list of
machine-chosen trades: contract, quantity, cost, worst-case loss, and the
gate evidence. Execution is a separate, human-confirmed step — see
robinhood_copilot_playbook.md.
"""
from __future__ import annotations

from typing import Any, Dict, List


def build_picklist(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Authorized evaluations -> ranked picks (highest net score first)."""
    picks = []
    for r in records:
        if r.get("type") != "evaluation":
            continue
        decision = r.get("decision", {})
        status = decision.get("Decision", {}).get("Status")
        if status not in ("AUTHORIZE", "FORCE_SHADOW"):
            continue
        option = r.get("option", {})
        risk = decision.get("Risk", {})
        scoring = decision.get("Scoring", {})
        qty = int(risk.get("Contract_Quantity", 0))
        mid = (float(option.get("bid", 0)) + float(option.get("ask", 0))) / 2.0
        picks.append({
            "ticker": r["ticker"],
            "setup": r["setup"],
            "contract": (f"{r['ticker']} {option.get('expiry', '?')} "
                         f"{option.get('strike', '?')}C"),
            "quantity": qty,
            "est_cost": round(mid * 100 * qty, 2),
            "worst_case_loss": round(float(risk.get("Total_Risk", 0.0)), 2),
            "worst_case_scenario": risk.get("Worst_Case_Scenario", ""),
            "net_score": scoring.get("Net_Score"),
            "invalidation_price": r.get("invalidation_price"),
            "rationale": r.get("rationale", ""),
        })
    return sorted(picks, key=lambda p: (-(p["net_score"] or 0), p["ticker"]))


def format_picklist(picks: List[Dict[str, Any]]) -> str:
    if not picks:
        return "No trades authorized today. NO TRADE is a valid outcome (§69)."
    lines = [f"PICK LIST — {len(picks)} authorized trade(s), ranked by net score", ""]
    for i, p in enumerate(picks, 1):
        lines += [
            f"{i}. {p['contract']}  x{p['quantity']}  [{p['setup']}, score {p['net_score']}]",
            f"   est. cost ${p['est_cost']:,.2f} | worst-case loss "
            f"${p['worst_case_loss']:,.2f} ({p['worst_case_scenario']})",
            f"   exit if underlying closes below {p['invalidation_price']}",
            f"   why: {p['rationale']}",
            "",
        ]
    lines.append('To execute, say: "execute the pick list" (human confirmation required).')
    return "\n".join(lines)
