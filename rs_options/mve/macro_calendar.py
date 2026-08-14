"""Static macro calendar (spec §11, §12): CSV file, weekly refresh by hand.

CSV columns: event, timestamp_utc (ISO-8601), tier, expected, prior
Event states (§12): PRE_EVENT / EVENT_WINDOW / POST_EVENT / NONE.
Tier-1 EVENT_WINDOW → MacroState.hard_block (no new trades).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from rs_options_risk import MacroState

PRE_EVENT_MIN = 60          # §12 default
EVENT_PRE_MIN = 15          # window opens this long before release
EVENT_POST_MIN = 30         # CALIBRATE — post-release settle time
POST_EVENT_MIN = 60         # POST_EVENT tail after the window closes


@dataclass(frozen=True)
class MacroEvent:
    event: str
    ts: datetime
    tier: int
    expected: float | None = None
    prior: float | None = None


def load_calendar(csv_path: str) -> list:
    events = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            ts = datetime.fromisoformat(row["timestamp_utc"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            events.append(MacroEvent(
                event=row["event"].strip(),
                ts=ts,
                tier=int(row["tier"]),
                expected=_num(row.get("expected")),
                prior=_num(row.get("prior")),
            ))
    return sorted(events, key=lambda e: e.ts)


def event_state(events: list, now: datetime) -> tuple:
    """Returns (state, event | None) for the most binding event at `now`."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    best = ("NONE", None)
    rank = {"NONE": 0, "POST_EVENT": 1, "PRE_EVENT": 2, "EVENT_WINDOW": 3}
    for e in events:
        delta_min = (e.ts - now).total_seconds() / 60.0
        if -EVENT_POST_MIN <= delta_min <= EVENT_PRE_MIN:
            state = "EVENT_WINDOW"
        elif EVENT_PRE_MIN < delta_min <= PRE_EVENT_MIN:
            state = "PRE_EVENT"
        elif -(EVENT_POST_MIN + POST_EVENT_MIN) <= delta_min < -EVENT_POST_MIN:
            state = "POST_EVENT"
        else:
            continue
        if rank[state] > rank[best[0]]:
            best = (state, e)
    return best


def macro_state(events: list, now: datetime) -> MacroState:
    """MacroState for the gate stack: Tier-1 EVENT_WINDOW → hard block."""
    state, event = event_state(events, now)
    if event is None:
        return MacroState(hard_block=False, label="")
    hard = state == "EVENT_WINDOW" and event.tier == 1
    return MacroState(hard_block=hard, label=f"{event.event}:{state}")


def _num(v):
    if v is None or str(v).strip() == "":
        return None
    return float(v)
