"""
BGF Decision Engine — implements the NPOS §III·02 if/then logic.
Evaluates performance metrics and returns a list of recommended interventions.
"""
from dataclasses import dataclass

@dataclass
class Intervention:
    issue: str
    action: str
    priority: str  # immediate | structural | monitor

CTR_STABLE_MIN = 6.0
CTR_STRONG_MIN = 10.0
RETENTION_30_MIN = 50.0
RETENTION_70_MIN = 35.0
SESSION_DEPTH_MIN = 1.5

def evaluate(metrics: dict) -> list[Intervention]:
    """
    metrics keys: ctr_24h, ctr_48h, retention_30, retention_70,
                  watch_time_sec, session_depth, shorts_views
    Returns list of Intervention objects.
    """
    interventions = []
    ctr_24 = metrics.get("ctr_24h", 0)
    ctr_48 = metrics.get("ctr_48h", 0)
    ret_30 = metrics.get("retention_30", 100)
    ret_70 = metrics.get("retention_70", 100)
    session = metrics.get("session_depth", 2.0)
    shorts = metrics.get("shorts_views", 0)

    # CTR Engine
    if ctr_24 < CTR_STABLE_MIN:
        interventions.append(Intervention(
            issue=f"CTR at 24h is {ctr_24}% (below {CTR_STABLE_MIN}% threshold)",
            action="Deploy thumbnail variant B. Do not change title yet.",
            priority="immediate"
        ))
    if ctr_48 < CTR_STABLE_MIN:
        interventions.append(Intervention(
            issue=f"CTR at 48h still {ctr_48}% after variant B deployment",
            action="Deploy disruption thumbnail concept. Rewrite title using stronger curiosity gap.",
            priority="immediate"
        ))

    # Retention Engine
    if ret_30 < RETENTION_30_MIN:
        interventions.append(Intervention(
            issue=f"Retention at 30% mark is {ret_30}% — hook failure",
            action="Pattern interrupt in next episode must be more aggressive. Rewrite opening 15 seconds.",
            priority="structural"
        ))
    if ret_70 < RETENTION_70_MIN:
        interventions.append(Intervention(
            issue=f"Retention at 70% mark is {ret_70}% — pacing/payoff failure",
            action="Mid-section pacing too slow. Increase curiosity gap frequency. Payoff must land earlier.",
            priority="structural"
        ))

    # Session depth
    if session < SESSION_DEPTH_MIN:
        interventions.append(Intervention(
            issue=f"Session depth {session} — viewers not continuing to next video",
            action="Bridge to next episode is not compelling. Rewrite final 60 seconds to create stronger loop.",
            priority="structural"
        ))

    # Shorts
    if shorts < 1000:
        interventions.append(Intervention(
            issue=f"Shorts underperforming ({shorts} views)",
            action="Replace first 3 seconds of top Shorts. Re-release with new hook lines.",
            priority="immediate"
        ))
    elif shorts > 50000:
        interventions.append(Intervention(
            issue=f"Shorts outperforming ({shorts} views) — replication opportunity",
            action="Extract hook structure and subject angle. Apply to 3 new Shorts immediately.",
            priority="immediate"
        ))

    if not interventions:
        interventions.append(Intervention(
            issue="No critical issues detected",
            action="Monitor. Replicate winner structure in next episode.",
            priority="monitor"
        ))

    return interventions

def interventions_to_dict(interventions: list[Intervention]) -> list[dict]:
    return [{"issue": i.issue, "action": i.action, "priority": i.priority}
            for i in interventions]
