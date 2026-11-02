# -*- coding: utf-8 -*-
"""V4 markets screen: only verified values as numbers, honest units, plain summaries."""
from datetime import date

import globalmkt
from dashboard.v4 import markets_data as M
from dashboard.v4 import markets_ui as MU


def _g(**over):
    rows = {
        "equity": [{"symbol": "^GSPC", "name": "S&P 500", "price": 7580.07, "d1": -1.82, "d7": -0.57, "d30": -1.13,
                    "trend": "יורדת ↓", "as_of": "30/10/2026"},
                   {"symbol": "^IXIC", "name": "Nasdaq", "price": 25437.0, "d1": -2.86, "as_of": "30/10/2026"},
                   {"symbol": "^VIX", "name": "VIX", "price": 19.42, "d1": 12.91, "as_of": "30/10/2026"}],
        "rates": [{"symbol": "^TNX", "name": "10Y", "price": 4.93, "d1": -1.2, "as_of": "30/10/2026"},
                  {"symbol": "2YY=F", "name": "2Y", "price": None, "d1": None},
                  {"symbol": "ILS=X", "name": "USD/ILS", "price": 3.108, "d1": -0.46, "as_of": "30/10/2026"}],
        "commodity": [{"symbol": "CL=F", "name": "WTI", "price": 104.12, "d1": 2.08, "as_of": "30/10/2026"},
                      {"symbol": "BZ=F", "name": "Brent", "price": 113.43, "d1": -1.26, "as_of": "30/10/2026"}],
        "crypto": [], "fx": []}
    rows.update(over)
    return {"schema": globalmkt.SCHEMA, "updated": date.today().strftime("%d/%m/%Y") + " 09:00", "groups": rows}


def test_yield_changes_are_in_basis_points():
    secs = {s["key"]: s for s in M.sections(globalmkt.check(_g()))}
    tnx = next(r for r in secs["rates"]["rows"] if r["sym"] == "^TNX")
    assert tnx["val"] == "4.93%" and tnx["d1"] == "−6 נ״ב"                       # 4.99% to 4.93%, not "−1.2%"
    assert "(−6 נ״ב)" in secs["rates"]["summary"]


def test_missing_and_unverified_values_never_show_as_numbers():
    g = globalmkt.check(_g())
    secs = {s["key"]: s for s in M.sections(g)}
    two = next(r for r in secs["rates"]["rows"] if r["sym"] == "2YY=F")
    assert two["status"] == "missing" and two["val"] == "אין נתון"
    assert "עקום התשואות" in secs["rates"]["note"]
    stale = globalmkt.check({**_g(), "updated": "01/01/2020 09:00"})
    assert all(r["status"] != "ok" for s in M.sections(stale) for r in s["rows"])
    assert MU.validation(M.validation(stale), True) == ""


def test_oil_benchmarks_that_disagree_are_named_not_averaged():
    secs = {s["key"]: s for s in M.sections(globalmkt.check(_g()))}
    assert secs["commodity"]["summary"].startswith("נפט WTI עלה (+2.08%) ונפט ברנט ירד (−1.26%).")


def test_system_calculations_are_dated_and_flagged_when_old():
    assert M.calc_age({"date": "25/10/2026"}, date(2026, 11, 1))["stale"] is True
    assert M.calc_age({"date": "31/10/2026"}, date(2026, 11, 1))["stale"] is False


def test_breadth_says_how_small_the_sample_is():
    b = M.breadth({"breadth": {"above50": 50.0, "above200": 65.0, "advancers": 8, "decliners": 12}})
    assert b["n"] == 20 and b["items"][2]["text"] == "8 מתוך 20"
    assert "מדגם קטן" in MU.breadth(b, False)


def _series(last, n=300, end="2026-10-30"):
    import pandas as pd
    idx = pd.bdate_range(end=end, periods=n)
    vals = [last * (0.9 + 0.1 * i / (n - 1)) for i in range(n)]
    return pd.Series(vals, index=idx)


def test_history_is_shown_only_when_it_matches_the_verified_value():
    g = globalmkt.check(_g())
    ok = M.history({"^GSPC": _series(7580.07)}, g)[0]
    assert ok["status"] == "ok" and ok["val"] == "7,580.07"
    bad = M.history({"^GSPC": _series(8000.0)}, g)[0]
    assert bad["status"] == "verify"
    tnx = next(r for r in M.history({"^TNX": _series(4.93)}, g) if r["sym"] == "^TNX")
    assert tnx["m3"].endswith("נ״ב")                                           # yields in basis points
