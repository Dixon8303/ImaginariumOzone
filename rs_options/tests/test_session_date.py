"""Sessions 2026-09-21 and 2026-09-25 were never traded. These pin the fix.

GitHub delivers scheduled fires late — by hours — so an after-close run
can land past midnight UTC. The workflow used to read "UTC hour >= 21" as
the only trade window, so a delivery at 00:05 briefed read-only instead,
and the session went unscanned, unordered and unexited. Nothing failed:
every run reported success, which is why it stayed invisible for two
sessions.

The workflow's shell is tested here rather than only the Python, because
the workflow is where the bug was.
"""
import pathlib
import shutil
import subprocess

import pytest
import yaml

from mve.report import save_report
from paper.daily import session_date_from_argv

# Resolved from this file, not the CWD: the suite is normally run from
# rs_options/ but must not depend on that.
WORKFLOW = (pathlib.Path(__file__).resolve().parents[2]
            / ".github" / "workflows" / "paper_trader.yml")


def gnu_date() -> bool:
    """The step uses `date -u -d`, which BSD date (macOS) rejects. Runners
    are ubuntu-latest, so skipping locally costs nothing."""
    return subprocess.run(["date", "-u", "-d", "2026-01-01", "+%F"],
                          capture_output=True).returncode == 0


needs_gnu_date = pytest.mark.skipif(
    not shutil.which("bash") or not gnu_date(),
    reason="step shell needs bash and GNU date -d")


def mode_step() -> str:
    with open(WORKFLOW) as f:
        spec = yaml.safe_load(f)
    step = next(s for s in spec["jobs"]["daily"]["steps"]
                if s.get("name") == "Select run mode")
    return (step["run"]
            .replace("${{ github.event_name }}", "schedule")
            .replace("${{ inputs.mode }}", ""))


def run_step(delivered: str) -> tuple:
    """(mode, session) the workflow picks for a fire delivered at `delivered`."""
    mock = f'''
    FAKE="{delivered}"
    date() {{
      local fmt="${{@: -1}}"
      if printf '%s\\n' "$@" | grep -q yesterday; then
        command date -u -d "$FAKE UTC - 1 day" "$fmt"
      else
        command date -u -d "$FAKE UTC" "$fmt"
      fi
    }}
    GITHUB_OUTPUT=$(mktemp)
    '''
    script = mock + mode_step() + "\ncat \"$GITHUB_OUTPUT\""
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    kv = dict(line.split("=", 1) for line in out.stdout.strip().splitlines()
              if "=" in line and line.split("=", 1)[0] in ("flag", "session"))
    mode = "preopen" if kv.get("flag") == "--preopen" else "trade"
    return mode, kv.get("session")


# ── the regression itself ─────────────────────────────────────────────
@needs_gnu_date
@pytest.mark.parametrize("delivered", ["2026-09-26 00:05", "2026-09-26 00:34"])
def test_the_deliveries_that_lost_a_session_now_trade_it(delivered):
    """Friday 2026-09-25's evening fires arrived after midnight. Both must
    now trade, and both must name Friday — not the runner's Saturday."""
    assert run_step(delivered) == ("trade", "2026-09-25")


@needs_gnu_date
def test_a_late_preopen_fire_still_only_briefs():
    """09-25 17:32 was a delayed morning cron. Widening the evening window
    must not turn a daytime delivery into a trading run."""
    assert run_step("2026-09-25 17:32") == ("preopen", "2026-09-25")


@needs_gnu_date
@pytest.mark.parametrize("delivered,mode,session", [
    ("2026-09-25 20:59", "preopen", "2026-09-25"),   # just outside
    ("2026-09-25 21:00", "trade",   "2026-09-25"),   # window opens
    ("2026-09-25 04:59", "trade",   "2026-09-24"),   # window closes
    ("2026-09-25 05:00", "preopen", "2026-09-25"),   # just outside
])
def test_window_edges(delivered, mode, session):
    assert run_step(delivered) == (mode, session)


@needs_gnu_date
@pytest.mark.parametrize("delivered,session", [
    ("2026-10-01 00:10", "2026-09-30"),
    ("2027-01-01 00:10", "2026-12-31"),
])
def test_post_midnight_rollback_crosses_month_and_year(delivered, session):
    assert run_step(delivered) == ("trade", session)


@needs_gnu_date
def test_a_sunday_session_is_named_and_left_to_the_freshness_guard():
    """A Monday 00:30 delivery resolves to Sunday. Trading it is correct to
    ATTEMPT — paper.daily's data_is_fresh then finds Friday's bar against a
    Sunday session and declines. The workflow must not silently skip it,
    and must not pretend Sunday is Friday."""
    assert run_step("2026-09-28 00:30") == ("trade", "2026-09-27")


# ── the plumbing the workflow depends on ──────────────────────────────
def test_session_date_defaults_to_today():
    from datetime import date
    assert session_date_from_argv(["paper.daily"]) == str(date.today())


@pytest.mark.parametrize("argv", [
    ["x", "--session-date=2026-09-25"],
    ["x", "--preopen", "--session-date=2026-09-25"],
    ["x", "--session-date=2026-09-25", "--preopen"],
])
def test_explicit_session_date_wins(argv):
    assert session_date_from_argv(argv) == "2026-09-25"


def test_a_malformed_session_date_is_rejected_loudly():
    """Silently falling back to today is how a misdated session gets
    traded against the wrong bars."""
    with pytest.raises(ValueError):
        session_date_from_argv(["x", "--session-date=2026-13-99"])


def test_report_header_can_be_stamped_with_the_session(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = save_report("t", "body", stamp="2026-09-25")
    assert open(path).readline().strip() == "generated: 2026-09-25"


def test_report_header_still_defaults_to_today(tmp_path, monkeypatch):
    from datetime import date
    monkeypatch.chdir(tmp_path)
    path = save_report("t", "body")
    assert open(path).readline().strip() == f"generated: {date.today()}"


# ── the digest's own version of the same midnight bug ─────────────────
# Shipped 2026-09-28 and immediately cried wolf: the 01:13 UTC run that
# correctly reported Monday was measured against Tuesday's calendar date
# and called STALE. A warning that fires when nothing is wrong is worse
# than none, because it trains the operator to ignore the real one.
def utc(ts: str):
    from datetime import datetime, timezone
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


@pytest.mark.parametrize("now,expected,why", [
    ("2026-09-29 01:13", "2026-09-28", "the run that cried wolf"),
    ("2026-09-29 01:52", "2026-09-28", "its duplicate fire"),
    ("2026-09-29 12:45", "2026-09-28", "pre-open: today has not closed"),
    ("2026-09-29 20:59", "2026-09-28", "one minute before the close bound"),
    ("2026-09-29 21:00", "2026-09-29", "after the close, today counts"),
    ("2026-09-26 01:13", "2026-09-25", "Saturday small hours -> Friday"),
    ("2026-09-27 12:00", "2026-09-25", "Sunday -> Friday"),
    ("2026-09-28 12:00", "2026-09-25", "Monday pre-open -> Friday"),
])
def test_last_completed_session(now, expected, why):
    from paper.notify import last_completed_session
    assert last_completed_session(utc(now)) == expected, why


def test_digest_does_not_cry_wolf_on_a_post_midnight_report(tmp_path, monkeypatch):
    """The exact shape of the 2026-09-28 run: report dated Monday, digest
    built at 01:13 UTC Tuesday. Must NOT be flagged stale."""
    import paper.notify as notify
    reports = tmp_path / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "paper_trading.txt").write_text(
        "generated: 2026-09-28\n\nPAPER SHADOW TRACK — as of 2026-09-28\n")
    (reports / "paper_growth.jsonl").write_text(
        '{"date": "2026-09-25", "equity": 100000.0}\n'
        '{"date": "2026-09-28", "equity": 96719.48}\n')
    monkeypatch.chdir(tmp_path)
    assert "STALE" not in notify.digest(utc("2026-09-29 01:13"))


def test_digest_still_flags_a_genuinely_missed_session(tmp_path, monkeypatch):
    """Same report, but two sessions have closed since. The warning has to
    survive the fix that silenced the false one."""
    import paper.notify as notify
    reports = tmp_path / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "paper_trading.txt").write_text("generated: 2026-09-28\n\nbody\n")
    (reports / "paper_growth.jsonl").write_text(
        '{"date": "2026-09-28", "equity": 96719.48}\n')
    monkeypatch.chdir(tmp_path)
    assert "STALE" in notify.digest(utc("2026-09-30 22:00"))
