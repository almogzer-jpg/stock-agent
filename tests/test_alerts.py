# -*- coding: utf-8 -*-
"""Alert Center: typed alerts from real signals."""
import pandas as pd
from conftest import base_metrics
from alerts.center import build_alerts

SECTORS = [{"sector": "טכנולוגיה", "score": 90, "rs": 7.0},
           {"sector": "אנרגיה", "score": 50, "rs": 0.0},
           {"sector": "נדל\"ן", "score": 12, "rs": -6.0}]


def _df():
    return pd.DataFrame([
        base_metrics({"Ticker": "AAA"}),                                   # breakout
        base_metrics({"Ticker": "VVV", "VolRatio": 2.5}),                  # volume spike
        base_metrics({"Ticker": "RRR", "Price": 80, "MA200": 100,
                      "RiskLevel": "גבוה"}),                               # risk warning
    ])


def test_breakout_is_information_not_a_buy_alert():
    alerts = build_alerts(_df(), SECTORS, {})
    brk = [a for a in alerts if a["scope"] == "AAA" and "פריצה" in a["type"]]
    assert brk and all(a["severity"] == "מידע" for a in brk)
    assert all("לא המלצת קנייה" in a["message"] for a in brk)


def test_volume_spike_alert():
    alerts = build_alerts(_df(), SECTORS, {})
    assert any(a["type"] == "זינוק נפח" and a["scope"] == "VVV" for a in alerts)


def test_earnings_alert_from_events():
    events = {"AAA": {"days_to_earnings": 3, "earnings_date": "2026-06-13"}}
    alerts = build_alerts(_df(), SECTORS, events)
    assert any(a["type"] == "דוחות" for a in alerts)


def test_analyst_alert_from_events():
    events = {"AAA": {"rating_action": "הורדת דירוג: Buy → Hold", "rating_firm": "X"}}
    alerts = build_alerts(_df(), SECTORS, events)
    assert any(a["type"] == "שינוי דירוג" and a["severity"] == "גבוהה" for a in alerts)


def test_earnings_today_reads_as_today_not_zero_days():
    events = {"AAA": {"days_to_earnings": 0, "earnings_date": "2026-10-29"}}
    msg = next(a["message"] for a in build_alerts(_df(), SECTORS, events) if a["type"] == "דוחות")
    assert "היום" in msg and "בעוד 0" not in msg


def test_reaffirmed_rating_is_not_an_alert():
    events = {"AAA": {"rating_action": "אישרור דירוג: קנייה", "rating_firm": "UBS"}}
    assert not any(a["type"] == "שינוי דירוג" for a in build_alerts(_df(), SECTORS, events))


def test_sector_rotation_alerts():
    alerts = build_alerts(_df(), SECTORS, {})
    rot = [a for a in alerts if a["type"] == "רוטציית סקטורים"]
    assert any("טכנולוגיה" in a["message"] for a in rot)   # strong in
    assert any("נדל" in a["message"] for a in rot)          # weak out


def test_all_alerts_have_fields_and_valid_severity():
    alerts = build_alerts(_df(), SECTORS, {})
    for a in alerts:
        assert all(k in a for k in ("type", "scope", "severity", "message"))
        assert a["severity"] in ("גבוהה", "בינונית", "מידע")


def test_alerts_sorted_by_severity():
    alerts = build_alerts(_df(), SECTORS, {})
    order = {"גבוהה": 0, "בינונית": 1, "מידע": 2}
    sev = [order[a["severity"]] for a in alerts]
    assert sev == sorted(sev)
