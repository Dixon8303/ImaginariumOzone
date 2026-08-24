"""Growth tracking — reporting only; must never touch position sizing."""
import pytest

from paper.growth_tracker import (format_growth, growth_summary,
                                  load_equity_history, record_equity)


# ------------------------------------------------------------- recording
def test_record_and_load_round_trip(tmp_path):
    path = str(tmp_path / "growth.jsonl")
    assert record_equity("2026-08-24", 29.00, path) is True
    assert record_equity("2026-08-25", 31.50, path) is True
    history = load_equity_history(path)
    assert [h["equity"] for h in history] == [29.00, 31.50]


def test_same_day_reruns_do_not_duplicate(tmp_path):
    """--preopen then the evening run, or a retried run, must not
    inflate the history with two rows for one session."""
    path = str(tmp_path / "growth.jsonl")
    record_equity("2026-08-24", 29.00, path)
    wrote = record_equity("2026-08-24", 29.00, path)
    assert wrote is False
    assert len(load_equity_history(path)) == 1


def test_a_later_same_day_value_does_not_overwrite_the_first(tmp_path):
    """The dedupe is by date, not value — the first snapshot of a
    session stands; this module never rewrites history."""
    path = str(tmp_path / "growth.jsonl")
    record_equity("2026-08-24", 29.00, path)
    record_equity("2026-08-24", 999.00, path)          # ignored
    history = load_equity_history(path)
    assert len(history) == 1 and history[0]["equity"] == 29.00


def test_missing_file_returns_empty_not_an_error(tmp_path):
    assert load_equity_history(str(tmp_path / "nope.jsonl")) == []


def test_a_torn_line_is_skipped_not_fatal(tmp_path):
    path = tmp_path / "growth.jsonl"
    path.write_text('{"date": "2026-08-24", "equity": 29.0}\n'
                    'not json at all\n'
                    '{"date": "2026-08-25", "equity": 30.0}\n')
    history = load_equity_history(str(path))
    assert [h["equity"] for h in history] == [29.0, 30.0]


# --------------------------------------------------------------- summary
def test_summary_needs_at_least_two_points():
    assert growth_summary([{"date": "2026-08-24", "equity": 29.0}]) == {}
    assert growth_summary([]) == {}


def test_summary_computes_delta_and_pct():
    hist = [{"date": "2026-08-24", "equity": 29.00},
            {"date": "2026-08-25", "equity": 31.90}]
    s = growth_summary(hist)
    assert s["delta"] == pytest.approx(2.90)
    assert s["pct"] == pytest.approx(0.10, abs=0.001)
    assert s["days_elapsed"] == 1


def test_summary_counts_flat_vs_moved_sessions():
    hist = [{"date": "2026-08-20", "equity": 29.0},
            {"date": "2026-08-21", "equity": 29.0},   # flat
            {"date": "2026-08-22", "equity": 29.0},   # flat
            {"date": "2026-08-23", "equity": 31.0},   # moved
            {"date": "2026-08-24", "equity": 31.0}]   # flat
    s = growth_summary(hist)
    assert s["days_with_a_change"] == 1
    assert s["days_flat"] == 3
    assert s["snapshots"] == 5


def test_summary_tracks_peak_trough_and_distance_to_doctrine_threshold():
    hist = [{"date": "2026-08-20", "equity": 29.0},
            {"date": "2026-08-21", "equity": 20.0},   # a loss: trough
            {"date": "2026-08-22", "equity": 45.0}]   # a win: peak
    s = growth_summary(hist)
    assert s["peak_equity"] == 45.0 and s["trough_equity"] == 20.0
    from paper.micro_sizing import MICRO_EQUITY_THRESHOLD
    assert s["to_doctrine_threshold"] == pytest.approx(
        MICRO_EQUITY_THRESHOLD - 45.0)


def test_distance_to_threshold_floors_at_zero_once_past_it():
    from paper.micro_sizing import MICRO_EQUITY_THRESHOLD
    hist = [{"date": "2026-08-20", "equity": 29.0},
            {"date": "2026-08-21", "equity": MICRO_EQUITY_THRESHOLD + 50}]
    s = growth_summary(hist)
    assert s["to_doctrine_threshold"] == 0.0


# ---------------------------------------------------------------- report
def test_format_growth_states_flatness_is_expected():
    hist = [{"date": "2026-08-20", "equity": 29.0},
            {"date": "2026-08-24", "equity": 31.0}]
    text = format_growth(growth_summary(hist))
    assert "29.00" in text and "31.00" in text
    assert "once every 10 trading days" in text
    assert "not a malfunction" in text


def test_format_growth_handles_too_little_history():
    text = format_growth({})
    assert "nothing to summarize yet" in text


def test_growth_module_never_imports_sizing_functions():
    """The non-martingale choice must be structural, not just a
    docstring promise: this module must have no way to influence how
    many shares a trade buys."""
    import ast
    import inspect

    import paper.growth_tracker as gt
    tree = ast.parse(inspect.getsource(gt))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(a.name for a in node.names)
    forbidden = {"position_size", "micro_position_size", "RISK_PCT",
                "MAX_POSITION_PCT"}
    assert not (names & forbidden), (
        f"growth_tracker imports sizing symbols: {names & forbidden}")
