"""What tick data does this account actually have? (H-27 Gate 1 census)

H-27's Gate 1 rules bar-only studies INADMISSIBLE: it needs the trades and
quotes tape, because the whole question is whether the trigger or the stop
printed first. That makes one unanswered question gate the entire entry —
is a SIP-class tape reachable on these credentials at all?

Nothing in this repo has ever asked. Every equity call passes
`"feed": "iex"` as a dict literal (`mve/alpaca_data.py`), never a
parameter, and `sip` appears nowhere. So the plan has been assumed, never
read, for the project's whole life.

Why this runs INSTEAD of a latency probe. Gate 0's other half, the latency
envelope, can only matter in a world where Gate 1 is satisfiable — and
satisfying Gate 1 means procuring a tape, which is the same decision as
choosing a routing class. Measure latency against today's path and the
number is either never used (the entry closed on data grounds) or obsolete
(the path changed). Worse, the only path available to measure is
`paper-api.alpaca.markets`, a simulator that performs no routing, so an
"order round trip" taken there omits the PFOF leg the source itself calls
dangerous. Gate 0's verdict is terminal by frozen text — "REJECTED,
regardless of every criterion below" — and a biased measurement behind an
irreversible verdict satisfies "measured, never assumed" in letter while
defeating it in substance.

This census is cheap, it is honest, and it can close the entry on its own.

    python -m mve.data_entitlement          # report to stdout + docs/reports/

Records STATUS CODES and RECORD COUNTS only. No market data is stored: the
reports directory is committed to a public repo.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

DATA_HOST = "https://data.alpaca.markets"
REPORT_PATH = os.path.join("docs", "reports", "data_entitlement.txt")
TIMEOUT = 30
PROBE_SYMBOL = "SPY"          # entitlement is plan-level, so the most
                              # liquid symbol isolates the plan from any
                              # per-symbol coverage question
WINDOW_MINUTES = 5
MAX_ERROR_CHARS = 300


def headers() -> dict:
    key = os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise SystemExit(
            "APCA_API_KEY_ID / APCA_API_SECRET_KEY are not set. This census "
            "needs them read-only; it places no orders and stores no market "
            "data. In CI they come from repository secrets.")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}


def probe(endpoint: str, feed: str, start: datetime, end: datetime,
          hdrs: dict) -> dict:
    """One GET. Returns status plus a record count — never the records."""
    params = {
        "start": start.isoformat().replace("+00:00", "Z"),
        "end": end.isoformat().replace("+00:00", "Z"),
        "limit": 100,
        "feed": feed,
    }
    url = (f"{DATA_HOST}/v2/stocks/{PROBE_SYMBOL}/{endpoint}"
           f"?{urllib.parse.urlencode(params)}")
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read())
        records = body.get(endpoint) or []
        return {"status": resp.status, "count": len(records), "error": ""}
    except urllib.error.HTTPError as e:
        # The error BODY is what distinguishes "no SIP on this plan" from
        # "no recent SIP on this plan" — a distinction the status code
        # alone hides, and the one that decides whether a paid upgrade
        # would even help.
        try:
            detail = e.read().decode("utf-8", "replace")[:MAX_ERROR_CHARS]
        except Exception:
            detail = ""
        return {"status": e.code, "count": 0, "error": detail.strip()}
    except Exception as e:
        return {"status": None, "count": 0, "error": f"{type(e).__name__}: {e}"}


def trading_day_back(today: date, days_back: int) -> date:
    """`days_back` calendar days ago, walked back to a weekday.

    The naive subtraction is what invalidated the 2026-10-12 census: 30 and
    400 days before that Monday are a Saturday and a Sunday, so the probe
    asked for five minutes of a closed market and every feed correctly
    returned zero records. The report then read those zeros as an
    entitlement finding and recommended closing H-27.

    Market holidays are still unknown here, which is why the IEX control
    exists — a holiday lands as a control failure, not a false verdict.
    """
    d = today - timedelta(days=days_back)
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d


def windows(today: date) -> list:
    """Two reaches. A plan can permit old SIP data and withhold recent, or
    withhold both; the study needs years of history, so both are asked.

    15:00 UTC is 11:00 ET — inside regular hours in both DST regimes.
    """
    def span(days_back: int) -> tuple:
        d = trading_day_back(today, days_back)
        anchor = datetime(d.year, d.month, d.day, 15, 0, tzinfo=timezone.utc)
        return anchor, anchor + timedelta(minutes=WINDOW_MINUTES)
    return [("recent (30d)", *span(30)), ("deep (400d)", *span(400))]


def run_census(today: date | None = None) -> dict:
    today = today or date.today()
    hdrs = headers()
    results = []
    for label, start, end in windows(today):
        for feed in ("iex", "sip"):
            for endpoint in ("trades", "quotes"):
                r = probe(endpoint, feed, start, end, hdrs)
                results.append({"window": label, "feed": feed,
                                "endpoint": endpoint, **r})
    return {"probed_symbol": PROBE_SYMBOL, "results": results}


def _all_returned_records(results: list, feed: str) -> bool:
    need = [(w, e) for w in ("recent (30d)", "deep (400d)")
            for e in ("trades", "quotes")]
    for window, endpoint in need:
        hit = next((r for r in results if r["feed"] == feed
                    and r["window"] == window
                    and r["endpoint"] == endpoint), None)
        if not hit or hit["status"] != 200 or hit["count"] == 0:
            return False
    return True


def control_ok(results: list) -> bool:
    """Did the probe retrieve anything AT ALL?

    IEX is the control, because it is the feed this repo has always used
    and is entitled to. If IEX returns no records, the probe retrieved
    nothing from anything and the SIP counts carry zero information about
    entitlement.

    The 2026-10-12 census had no such check: it read a weekend's empty
    tape as proof SIP was denied and recommended closing H-27 on that
    basis. A census that renders a verdict while its own control is
    failing is worse than one that refuses to answer.
    """
    return _all_returned_records(results, "iex")


def sip_is_usable(results: list) -> bool:
    """SIP counts as usable only when BOTH tapes return records at BOTH
    reaches. A 200 with zero records is not entitlement — and a tape that
    stops short of the study period cannot supply it either.

    Only meaningful when `control_ok` holds; callers must check that
    first, because this cannot distinguish "SIP withheld" from "the probe
    asked the wrong question".
    """
    return _all_returned_records(results, "sip")


def format_census(census: dict) -> str:
    results = census["results"]
    lines = [
        "H-27 GATE 1 DATA CENSUS — can this account reach a SIP-class tape?",
        "",
        f"probe symbol: {census['probed_symbol']}   "
        f"window: {WINDOW_MINUTES} minutes   stored: status codes and counts only",
        "",
        f"{'window':<14} {'feed':<5} {'endpoint':<9} {'status':<7} {'records':<8}",
        "-" * 54,
    ]
    for r in results:
        status = str(r["status"]) if r["status"] is not None else "ERR"
        lines.append(f"{r['window']:<14} {r['feed']:<5} {r['endpoint']:<9} "
                     f"{status:<7} {r['count']:<8}")

    errors = [r for r in results if r["error"]]
    if errors:
        lines += ["", "errors as returned (verbatim, truncated):"]
        for r in errors:
            lines.append(f"  {r['feed']}/{r['endpoint']} {r['window']}: "
                         f"{r['error']}")

    lines += ["", "=" * 54, ""]
    if not control_ok(results):
        lines += [
            "NO VERDICT — the control condition failed.",
            "",
            "The IEX feed returned no records either. IEX is the feed this",
            "repo has always used and is entitled to, so its silence means",
            "the probe retrieved nothing from anything: the SIP counts above",
            "say nothing whatever about entitlement.",
            "",
            "Likely causes, in order: the probed window fell on a market",
            "holiday; the credentials lack market-data access; the vendor",
            "was unreachable. Check the status codes and any error text",
            "above before re-running.",
            "",
            "This is exactly the state the 2026-10-12 census was in when it",
            "reported SIP as unusable and recommended closing H-27. It had",
            "asked for five minutes of a Saturday. No conclusion about the",
            "data plan may be drawn from a run in this state, and H-27's",
            "disposition is unchanged by it.",
        ]
        return "\n".join(lines)

    if sip_is_usable(results):
        lines += [
            "SIP-class trades AND quotes returned records at both reaches.",
            "",
            "Gate 1's data requirement is therefore NOT ruled out on",
            "entitlement grounds. It is not yet satisfied either: the tape",
            "must still cover every scanned candidate from one consistent",
            "pull (LAW 18), and coverage on $2-$20 low-float names at",
            "RVOL >= 5 is a separate question this census does not answer.",
            "",
            "Gate 0's latency half stays UNMEASURED, deliberately. It must",
            "be measured on whichever execution path is actually chosen —",
            "not on paper-api.alpaca.markets, which performs no routing and",
            "would understate the envelope on the exact leg that matters.",
        ]
    else:
        lines += [
            "SIP-class tick data is NOT usable on this account.",
            "",
            "Gate 1 is unsatisfiable as written, and the shortfall is in the",
            "inputs the frozen text names, not in their quality:",
            "",
            "  - 'the prevailing offer' is the NBBO. A single-venue book",
            "    cannot supply it, so every modelled fill would be priced",
            "    against the wrong quote.",
            "  - 'intrabar sequencing taken from the actual tick sequence,",
            "    never assumed' is the entry's whole content. On a thin name",
            "    the trigger and stop prints may not exist on one venue at",
            "    all — unobservable, not merely noisy.",
            "  - LULD halts are SIP messages, and the entry requires they be",
            "    handled explicitly rather than skipped silently. Halts are",
            "    frequent on exactly these symbol-days.",
            "  - LAW 18 aborts a study on a partial symbol-day. A",
            "    single-venue tape on a thin name is partial by construction,",
            "    which makes this fatal rather than survivable.",
            "",
            "The honest disposition is to close H-27 INCONCLUSIVE on data",
            "grounds, citing this census. INCONCLUSIVE, not FAILED: an",
            "unmeasurable claim has not been disproven, and the registration",
            "reserves FAILED for a claim the data contradicted.",
            "",
            "Closing it this way costs nothing further. The alternative is to",
            "procure a SIP-class tape, which is the same decision as choosing",
            "a routing class — and the method's own author holds that",
            "direct-access routing is necessary for sub-minute execution.",
        ]
    lines += [
        "",
        "Either way this census does not close Gate 0 by itself, and no",
        "number here may be composed into one. Recording the verdict in",
        "docs/PREREGISTERED.md is the operator's decision.",
    ]
    return "\n".join(lines)


def main() -> None:
    from .report import save_report
    census = run_census()
    text = format_census(census)
    print(text)
    print(f"\nReport saved: {save_report('data_entitlement', text)}")


if __name__ == "__main__":
    main()
