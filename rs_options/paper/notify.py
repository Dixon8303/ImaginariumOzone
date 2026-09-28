"""Phone-sized digest of the paper shadow track, for push delivery.

Reads only what `paper.daily` already committed to docs/reports/ — no
broker calls, no credentials, stdlib only. A notifier that could fail on
a missing dependency or an expired key would take the trading job down
with it, so it does neither.

    python -m paper.notify            # digest to stdout
    python -m paper.notify --full     # digest + the whole report

Telegram caps a message at 4096 characters and the full report runs
~5KB, so the digest is what gets pushed and the report stays a link.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta

REPORT = os.path.join("docs", "reports", "paper_trading.txt")
GROWTH = os.path.join("docs", "reports", "paper_growth.jsonl")
REPORT_URL = ("https://github.com/Dixon8303/ImaginariumOzone/blob/main/"
              "rs_options/docs/reports/paper_trading.txt")


def _read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def growth_rows() -> list:
    rows = []
    for line in _read(GROWTH).splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def last_weekday(today: date) -> date:
    """Most recent Mon-Fri on or before `today`. Market holidays are not
    known here, so a stale flag says what it sees, never 'the job failed'."""
    d = today
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d


def find(pattern: str, text: str, group: int = 1):
    m = re.search(pattern, text)
    return m.group(group) if m else None


def digest(today: date | None = None) -> str:
    today = today or date.today()
    report = _read(REPORT)
    rows = growth_rows()

    if not report or not rows:
        return ("RS paper track: no report on disk. Either the trader has "
                f"never run or the checkout is incomplete.\n{REPORT_URL}")

    generated = find(r"generated: (\d{4}-\d{2}-\d{2})", report) or "unknown"
    equity = float(rows[-1]["equity"])
    start = float(rows[0]["equity"])
    prev = float(rows[-2]["equity"]) if len(rows) > 1 else equity

    total_pct = (equity - start) / start * 100 if start else 0.0
    day_delta = equity - prev

    lines = [f"RS paper track — {generated}"]

    expected = last_weekday(today).isoformat()
    if generated != "unknown" and generated < expected:
        lines.append(
            f"STALE: newest report is {generated}, but {expected} has "
            "already traded. A session may have been skipped — check the "
            "trader's run mode, not just its exit code.")

    lines += [
        "",
        f"equity ${equity:,.2f}   ({total_pct:+.1f}% from ${start:,.0f})",
        f"last session {day_delta:+,.2f}",
    ]

    slots = re.search(
        r"OPEN POSITIONS \((\d+)\) — (\d+) of (\d+) stock slots used, "
        r"(\d+) option contracts", report)
    if slots:
        lines.append(
            f"open {slots.group(1)}: {slots.group(2)}/{slots.group(3)} stock "
            f"slots, {slots.group(4)} contracts")

    signals = find(r"TODAY'S SIGNALS \((\d+)\)", report)
    orders = find(r"PAPER ORDERS PLACED \((\d+)\)", report)
    if signals is not None:
        placed = f", {orders} order(s) placed" if orders else ""
        lines.append(f"signals {signals}{placed}")

    record = find(r"CUMULATIVE RECORD: (.+)", report)
    if record:
        lines.append(f"record: {record.strip()}")

    lines += ["", REPORT_URL]
    return "\n".join(lines)


def main() -> None:
    import sys
    text = digest()
    if "--full" in sys.argv:
        text += "\n\n" + "-" * 40 + "\n" + _read(REPORT)
    print(text)


if __name__ == "__main__":
    main()
