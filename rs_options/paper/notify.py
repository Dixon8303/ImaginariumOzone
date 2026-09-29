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
from datetime import datetime, timedelta, timezone

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


CLOSE_HOUR_UTC = 21          # NYSE close, year-round upper bound


def last_completed_session(now: datetime) -> str:
    """The newest session that has FINISHED, as of `now` (UTC).

    The hour test is the whole point. A session is not complete until the
    21:00 UTC close, so before then the newest finished session is
    yesterday's. Comparing against the runner's calendar date instead made
    this cry wolf every single night: the 01:13 UTC run that correctly
    reported Monday was measured against Tuesday and called stale. A
    staleness warning that fires when nothing is wrong trains the operator
    to ignore the one that matters.

    Market holidays are not known here, so the flag reports what it sees
    and never claims the job failed.
    """
    d = now.date() if now.hour >= CLOSE_HOUR_UTC else now.date() - timedelta(days=1)
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d.isoformat()


def find(pattern: str, text: str, group: int = 1):
    m = re.search(pattern, text)
    return m.group(group) if m else None


def digest(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
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

    expected = last_completed_session(now)
    if generated != "unknown" and generated < expected:
        lines.append(
            f"STALE: newest report is {generated}, but {expected} has "
            "already closed. A session may have been skipped — check the "
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
