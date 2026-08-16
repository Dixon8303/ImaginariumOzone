"""Broker trade-journal analyzer (Schwab/thinkorswim CSV export)."""
import pytest

from mve.trade_journal import analyze, load_rows, parse_money, summary

CSV = '''"Transactions for account Individual XXX262 as of 08/16/2026"
"Date","Action","Symbol","Description","Quantity","Price","Fees & Comm","Amount"
"01/10/2026","Sell to Close","XYZ 03/20/2026 50.00 C","CALL XYZ","1","0.50","$0.65","$49.35"
"01/08/2026","Buy to Open","XYZ 03/20/2026 50.00 C","CALL XYZ","1","1.00","$0.65","-$100.65"
"01/07/2026","Buy","DEF","DEF CORP","5","20.00","","-$100.00"
"01/05/2026","Sell","ABC","ABC INC","10","12.00","$0.10","$119.90"
"01/05/2026","Buy","ABC","ABC INC","10","10.00","","-$100.00"
"01/02/2026","MoneyLink Transfer","","FUNDS RECEIVED","","","","$250.00"
'''


@pytest.fixture
def result(tmp_path):
    p = tmp_path / "Individual_XXX262_Transactions_20260816-014100.csv"
    p.write_text(CSV)
    return analyze(load_rows(str(p)))


def test_parse_money_forms():
    assert parse_money("$1,234.56") == 1234.56
    assert parse_money("-$123.45") == -123.45
    assert parse_money("($123.45)") == -123.45
    assert parse_money("") == 0.0


def test_round_trips_and_fifo(result):
    trades = sorted(result["trades"], key=lambda t: t["exit"])
    assert len(trades) == 2
    # ABC: intraday +$19.90 net of fees baked into Amount
    assert trades[0]["entry"] == trades[0]["exit"]          # day trade
    assert trades[0]["pnl"] == pytest.approx(19.90)
    # option: amount-based per-unit cash handles the x100 multiplier
    assert trades[1]["pnl"] == pytest.approx(49.35 - 100.65)
    assert result["open_positions"] == 1                     # DEF never sold


def test_contributions_and_fees(result):
    assert result["contributions"] == pytest.approx(250.0)
    assert result["fees"] == pytest.approx(0.10 + 0.65 + 0.65)


def test_short_round_trip(tmp_path):
    csv_text = '''"Date","Action","Symbol","Description","Quantity","Price","Fees & Comm","Amount"
"01/06/2026","Buy to Cover","GME","GME","10","8.00","","-$80.00"
"01/04/2026","Sell Short","GME","GME","10","10.00","","$100.00"
'''
    p = tmp_path / "t.csv"
    p.write_text(csv_text)
    trades = analyze(load_rows(str(p)))["trades"]
    assert len(trades) == 1
    assert trades[0]["pnl"] == pytest.approx(20.0)           # short profit


def test_summary_is_aggregate_only(result):
    text = summary(result)
    assert "TRADE JOURNAL" in text
    assert "win rate" in text and "expectancy" in text
    assert "net contributions" in text and "$+250.00" in text
    assert "LAW 19" in text and "provisional" in text        # small-n warning
    assert "XXX262" not in text and "ABC" not in text        # no identifiers
