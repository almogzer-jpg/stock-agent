# -*- coding: utf-8 -*-
"""V4 alerts: grouped by importance, plain wording, the live assessment as the tag."""
from datetime import date

import stockdata
from dashboard.v4 import alerts_data as A
from dashboard.v4 import alerts_ui as AU


def _rows():
    today = date.today().strftime("%d/%m/%Y")
    base = {"Date": today, "MA50": 95.0, "MA200": 110.0, "RSI14": 40.0, "Completeness": 100, "RiskLevel": "גבוה",
            "Support": 92.0, "Price": 100.0, "_tier": "full", "ScoreV2": 50, "DailyChange%": -5.48, "VolRatio": 2.5}
    return {"AVGO": {**base, "Ticker": "AVGO", "Name": "Broadcom Inc."}}


ALERTS = [
    {"type": "אזהרת סיכון", "scope": "AVGO", "severity": "גבוהה", "message": "AVGO — סיכון גבוה ומתחת לממוצע 200"},
    {"type": "זינוק נפח", "scope": "AVGO", "severity": "בינונית", "message": "AVGO — נפח מסחר פי 2.5 מהממוצע"},
    {"type": "רוטציית סקטורים", "scope": "בריאות", "severity": "מידע", "message": "..."},
]
MKT = {"sectors": [{"sector": "בריאות", "score": 96, "rs": 12.36}]}


def test_alerts_are_grouped_and_tagged_with_the_live_assessment():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    d = A.build(ALERTS, rows, vmap, {}, MKT, "30/10/2026", date(2026, 11, 1))
    assert d["counts"] == {"critical": 1, "important": 1, "info": 1}
    risk = d["items"][0]
    assert risk["title"] == "Broadcom: סיכון גבוה ומגמת ירידה"
    assert "ירדה 5.48% ביום המסחר האחרון" in risk["text"]
    assert risk["tag"]["label"] == vmap["AVGO"]["label"]
    sector = d["items"][2]
    assert sector["link"] == "markets" and sector["tag"] is None
    assert sector["text"].startswith("חוזק יחסי של 12.4% מעל S&P 500 בחודש האחרון.")


def test_no_personal_filter_and_no_advice_wording():
    html = AU.rules(False) + AU.rules(True)
    assert "הרשימה שלי" not in html and "התראה היא מידע, לא המלצה" in html
