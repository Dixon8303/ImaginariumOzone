#!/usr/bin/env python3
"""
Set a CinemaWin user's plan directly in SQLite.

Usage (from cinemawin/backend):
    python tools/set_plan.py you@email.com premium

Plans: entry | starter | premium
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip())
        return 2
    email = argv[1].strip().lower()
    plan = argv[2].strip().lower()
    if plan not in config.VALID_PLANS:
        print(f"error: plan must be one of {', '.join(config.VALID_PLANS)} (got {plan!r})")
        return 2
    if not config.DATABASE_PATH.exists():
        print(f"error: database not found at {config.DATABASE_PATH} (start the server once first)")
        return 1

    conn = sqlite3.connect(str(config.DATABASE_PATH))
    try:
        cur = conn.execute("SELECT id, plan FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if row is None:
            print(f"error: no user with email {email!r}")
            return 1
        conn.execute("UPDATE users SET plan = ? WHERE email = ?", (plan, email))
        conn.commit()
        print(f"{email} ({row[0]}): plan {row[1]} -> {plan}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
