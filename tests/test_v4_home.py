# -*- coding: utf-8 -*-
"""V4 home screen: live-engine verdicts only, honest market story, real dates."""
import os
import re
from datetime import date

import stockdata
from dashboard.v4 import home_data as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V4_DIR = os.path.join(ROOT, "dashboard", "v4")


def test_v4_never_reads_the_shadow_engine():
    """Owner rule 01/11/2026: no shadow conclusion is shown before the switch is approved."""
    for name in os.listdir(V4_DIR):
        if name.endswith(".py"):
            src = open(os.path.join(V4_DIR, name), encoding="utf-8").read()
            assert not re.search(r"verdict4|shadow_verdicts|import shadow|SHADOW_", src), name


def _rows():
    today = date.today().strftime("%d/%m/%Y")
    base = {"Date": today, "MA50": 95.0, "MA200": 90.0, "RSI14": 60.0, "Completeness": 100, "RiskLevel": "נמוך",
            "Support": 92.0, "Resistance": 110.0, "DistSupport%": -8.0, "DistResistance%": 10.0,
            "RevenueGrowth": 18.0, "OperatingMargin": 25.0, "ROIC": 20.0, "DebtToEquity": 0.3, "_tier": "full"}
    return {
        "AAA": {**base, "Ticker": "AAA", "Name": "Alpha Holdings Corporation", "Price": 100.0, "ScoreV2": 80, "DailyChange%": 1.2},
        "BBB": {**base, "Ticker": "BBB", "Name": "Beta Inc.", "Price": 100.0, "ScoreV2": 72, "DailyChange%": -0.4},
        "CCC": {**base, "Ticker": "CCC", "Name": "Gamma Corp", "Price": 80.0, "ScoreV2": 60, "DailyChange%": -2.0},
    }


def test_picks_are_the_live_buys_in_the_live_order():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    pk = H.picks(rows, vmap, limit=3)
    assert [c["ticker"] for c in pk["cards"]] == ["AAA", "BBB"]          # CCC is not a live buy
    assert pk["total"] == 2
    for c in pk["cards"]:
        assert c["label"] == vmap[c["ticker"]]["label"] and c["why"] == vmap[c["ticker"]]["why"]
    assert pk["cards"][0]["name"] == "Alpha"


def test_card_answers_come_from_the_live_verdict():
    rows = _rows()
    v = stockdata.verdicts(rows)["AAA"]
    dims = {d["k"]: d for d in H.card_dims(v, rows["AAA"])}
    assert dims["חברה"]["v"] == v["facets"]["quality"]["label"].replace("חברה ", "")
    assert dims["מגמה"]["v"] == "חיובית" and dims["סיכון"]["v"] == "נמוך"


def _global(spx=-1.8, nas=-2.9, vix=12.9, status="ok"):
    strip = [{"symbol": "^GSPC", "price": 7580.07, "d1": spx}, {"symbol": "^IXIC", "price": 25437.0, "d1": nas},
             {"symbol": "^VIX", "price": 19.42, "d1": vix, "as_of": "30/10/2026"}]
    return {"status": status, "message": "" if status == "ok" else "הנתונים מוסתרים", "strip": strip, "updated": "01/11/2026 09:00"}


MKT = {"regime": {"score": 61}, "sectors": [
    {"sector": "בריאות", "score": 96, "change_pct": 0.4}, {"sector": "צריכה בסיסית", "score": 93, "change_pct": 0.2},
    {"sector": "אנרגיה", "score": 90, "change_pct": 0.1}, {"sector": "טכנולוגיה", "score": 16, "change_pct": -3.0},
    {"sector": "שירותי תקשורת", "score": 1, "change_pct": -2.5}]}


def test_market_story_on_the_30_10_2026_down_day():
    s = H.market_story(_global(), MKT)
    assert s["state"] == "neutral" and s["label"] == "ניטרלי"
    assert s["headline"] == "יום של ירידות, בעיקר בטכנולוגיה. הענפים הדפנסיביים החזיקו מעמד."
    assert "VIX" in s["body"] and "19.4" in s["body"]
    vix = s["figures"][2]
    assert vix["tone"] == "negative"                                   # a rising fear index is bad news


def test_market_story_hides_figures_when_data_is_not_verified():
    s = H.market_story(_global(status="unverified"), MKT)
    assert s["figures"] == [] and s["status"] == "unverified" and s["message"]
    assert "19.4" not in s["body"]


def test_week_lists_upcoming_earnings_by_date():
    rows = _rows()
    events = {"AAA": {"earnings_date": "2026-11-03"}, "BBB": {"earnings_date": "2026-11-02"},
              "CCC": {"earnings_date": "2026-12-20"}}
    w = H.week(events, rows, _global(), date(2026, 11, 1))
    assert [x["title"] for x in w[:2]] == ["Beta מפרסמת דוחות", "Alpha מפרסמת דוחות"]
    assert w[1]["date"] == "03/11" and w[1]["day"] == "שלישי"
    assert "הרשימה" not in w[0]["text"]
    assert any("התנודתיות עלתה" == x["title"] for x in w)
    assert all("Gamma" not in x["title"] for x in w)                  # beyond 7 days


def test_v4_has_no_personal_list():
    """Owner decision 01/11/2026: no personal lists until sign-in exists. V4 neither
    reads nor writes the stored list, and has no page, link or button for it."""
    for name in os.listdir(V4_DIR):
        if name.endswith(".py"):
            src = open(os.path.join(V4_DIR, name), encoding="utf-8").read()
            assert not re.search(r'"watch"|watchlist\(|set_watch|my-list|הרשימה שלי|לרשימה שלי', src), name


def test_short_names():
    assert [H.short_name(n) for n in ("Apple Inc.", "Eli Lilly and Company", "ExxonMobil Holdings Corporation")] == \
        ["Apple", "Eli Lilly", "ExxonMobil"]
    assert H.short_name("Vertex Pharmaceuticals Incorpor") == "Vertex Pharmaceuticals"


def test_browser_storage_uses_a_slot_per_key():
    src = open(os.path.join(ROOT, "dashboard", "localstore", "__init__.py"), encoding="utf-8").read()
    js = open(os.path.join(ROOT, "dashboard", "localstore", "index.html"), encoding="utf-8").read()
    assert "name=key" in src and "args.name" in js and "stockagent:default" in js   # with migration of old lists
