"""H-29 guards (registered 2026-11-18 in docs/PREREGISTERED.md).

The registration froze an instrument list, a window and a criterion
before any study code existed, and forbade any execution path until a
verdict. These tests are the mechanical half of that promise.
"""
import pathlib
import re

from mve.setups import ACTIVE_SETUPS
from mve.universe import UNIVERSE

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRY = (ROOT / "docs" / "PREREGISTERED.md").read_text().split(
    "## H-29 —", 1)[1].split("\n## ", 1)[0]

REGISTERED = set(
    "AAL AAPL ABBV AMD AMZN BA BAC COIN CRM CVX DAL DIS F GOOGL HOOD JPM KO "
    "META MSFT MU NFLX NVDA ORCL PFE PLTR PYPL RTX SBUX SOFI T TSLA UNH V VZ "
    "WMT XOM".split())


def test_instruments_are_the_36_single_stocks_frozen_at_registration():
    assert len(REGISTERED) == 36
    listed = set(re.findall(r"\b[A-Z]{1,5}\b", ENTRY.split(
        "**Instruments:", 1)[1].split("IWM, QQQ", 1)[0]))
    assert REGISTERED <= listed


def test_registered_list_matched_the_universe_on_the_day():
    """If UNIVERSE later grows, H-29 does NOT grow with it: the study
    reads the frozen list above, never UNIVERSE."""
    singles = {t for t in UNIVERSE if t not in ("IWM", "QQQ", "SPY")}
    assert REGISTERED <= singles


def test_window_and_criterion_numbers_are_frozen():
    for fixed in ("ending\n**2026-11-13**", "**5 bp round trip**",
                  "**>= +0.10R**", "**>= 250 sessions**",
                  "**break-even friction >= 10 bp**",
                  "more than 20%", "Entry + 2.0 x (entry − stop)",
                  "the **stop** fills first"):
        assert fixed in ENTRY, fixed


def test_iex_only_data_cannot_confirm():
    assert "INCONCLUSIVE (data)" in ENTRY


def test_status_open_and_no_execution_path():
    assert "**Status:** OPEN" in ENTRY
    assert not any("ORB" in s or "H-29" in s for s in ACTIVE_SETUPS)
    paper = ROOT / "paper"
    for path in paper.glob("*.py"):
        text = path.read_text()
        assert "H-29" not in text and "opening_range" not in text, path
