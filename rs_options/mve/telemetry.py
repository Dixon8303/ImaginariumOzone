"""Telemetry JSONL writer (spec §62, §63).

Every evaluated candidate is logged — authorized AND rejected — with the
risk engine's telemetry blocks (which carry Gate_Margins forensics).
One JSON object per line; append-only.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict


class TelemetryLog:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def write(self, record: Dict[str, Any]) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def records(self) -> list:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def rejection_summary(self) -> Dict[str, int]:
        """§63 weekly aggregate: which gate kills the most signals."""
        counts: Dict[str, int] = {}
        for r in self.records():
            decision = r.get("decision", {}).get("Decision", {})
            if decision.get("Status") in ("REJECT", "FREEZE", "HALT"):
                for reason in decision.get("Reasons", []):
                    counts[reason] = counts.get(reason, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
