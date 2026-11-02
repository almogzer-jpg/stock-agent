# -*- coding: utf-8 -*-
"""V4 opportunities screen and the home sector-concentration note: live verdicts
only, the live order, honest counts, and no forced sector diversity."""
from datetime import date

import stockdata
from dashboard.v4 import home_data as H
from dashboard.v4 import opps_data as O
from dashboard.v4 import ui


def _rows():
    today = date.today().strftime("%d/%m/%Y")
    base = {"Date": today, "MA50": 95.0, "MA200": 90.0, "RSI14": 60.0, "Completeness": 100, "RiskLevel": "נמוך",
            "Support": 92.0, "Resistance": 110.0, "Price": 100.0, "_tier": "enriched", "Name": "X Inc."}
    spec = [("E1", "Energy", 90, 1.0), ("E2", "Energy", 89, 2.0), ("E3", "Energy", 87, -1.0),
            ("H1", "Healthcare", 86, 0.5), ("T1", "Technology", 60, 3.0), ("W1", "Technology", 40, 0.1)]
    rows = {t: {**base, "Ticker": t, "Name": f"{t} Corp", "Sector": s, "ScoreV2": q, "DailyChange%": c} for t, s, q, c in spec}
    rows["H1"]["RiskLevel"] = "בינוני"
    rows["N1"] = {"Ticker": "N1", "Price": 50.0, "Score": 70, "_tier": "technical", "Date": today}
    return rows


def test_tabs_are_the_live_actions_in_the_live_order():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    tb = O.table(rows, vmap, "buy")
    assert [r["ticker"] for r in tb["rows"]] == [v["ticker"] for v in stockdata.ranked(vmap, rows, "buy")]
    for r in tb["rows"]:
        assert r["label"] == vmap[r["ticker"]]["label"] and r["why"] == vmap[r["ticker"]]["why"]
    cov = O.coverage(rows, vmap)
    assert cov["buy"] == len(tb["rows"]) == 4 and cov["rated"] == 6 and cov["all"] == 7 and cov["unrated"] == 1


def test_filters_and_sort():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    assert [r["ticker"] for r in O.table(rows, vmap, "buy", sector="אנרגיה")["rows"]] == ["E1", "E2", "E3"]
    assert [r["ticker"] for r in O.table(rows, vmap, "buy", risk="בינוני")["rows"]] == ["H1"]
    assert O.table(rows, vmap, "buy", sort="change")["rows"][0]["ticker"] == "E2"
    stale = O.table(rows, vmap, "buy", sector="נדל\"ן")            # a sector the tab does not have
    assert stale["sector"] == O.ALL and len(stale["rows"]) == 4
    assert O.table(rows, vmap, "buy")["sectors"][0] == {"name": "אנרגיה", "n": 3}


def test_unrated_stocks_are_counted_and_explained_not_hidden():
    rows = _rows()
    cov = O.coverage(rows, stockdata.verdicts(rows))
    text = O.coverage_text(cov)
    assert "6 מתוך 7" in text and "תנועת המחיר האחרונה" in text


def test_concentration_note_explains_without_reordering():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    pk = H.picks(rows, vmap, limit=3)
    assert [c["ticker"] for c in pk["cards"]] == ["E1", "E2", "E3"]          # the engine's order, untouched
    c = H.concentration(pk)
    assert c["sector"] == "אנרגיה" and c["k"] == 3
    assert c["text"].startswith("כל שלוש המניות כאן מאותו ענף: אנרגיה.")
    assert "4 המניות" in c["text"] and "2 ענפים" in c["text"]
    assert "והבאה בתור: 86" in c["detail"]


def test_no_note_when_the_picks_are_mixed():
    rows = _rows()
    rows["E2"]["Sector"] = rows["E3"]["Sector"] = "Healthcare"
    rows["H1"]["Sector"] = "Technology"
    vmap = stockdata.verdicts(rows)
    pk = H.picks(rows, vmap, limit=2)
    assert H.concentration(pk) is None


def test_numbers_keep_their_sign_inside_hebrew_text():
    out = ui.text("המכירות גדלות מהר (+39.1% בשנה). ציון 86 מתוך 100.")
    assert '<span class="v4-num">+39.1%</span>' in out and '<span class="v4-num">100</span>.' in out
    assert 'כ-<span class="v4-num">38</span>' in ui.text("נשארים כ-38 דולר")
    assert '<span class="v4-num">−2.5%</span>' in ui.text("ירידה של −2.5%")
