"""Committable study reports — the operator <-> cloud bridge.

Every research CLI saves its printed summary to docs/reports/<name>.txt
(relative to rs_options/, where the CLIs run). The operator commits and
pushes that folder; the cloud session reads results straight from the
repo instead of relying on pasted terminal output.

Contents are AGGREGATE STATISTICS ONLY — never keys, account values, or
raw vendor data (the data/ store stays local and uncommitted).
"""
from __future__ import annotations

import os
from datetime import date

REPORT_DIR = os.path.join("docs", "reports")

COMMIT_HINT = (
    "  git add docs/reports && git commit -m \"research reports\" && git push"
)


def save_report(name: str, text: str) -> str:
    """Write `text` to docs/reports/<name>.txt (overwrites the previous
    run — git history keeps the old ones). Returns the path written."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"{name}.txt")
    with open(path, "w") as f:
        f.write(f"generated: {date.today()}\n\n{text.rstrip()}\n")
    return path


def save_and_print(name: str, text: str) -> None:
    """The standard CLI tail: print the summary, save it, say how to ship it."""
    print(text)
    path = save_report(name, text)
    print(f"\nReport saved: {path}")
    print("Commit and push so the cloud session can read it:")
    print(COMMIT_HINT)
