# -*- coding: utf-8 -*-
"""V4 company analysis: the live verdict only, its real gates, price kept apart
from the decision, no invented prices, and contradictions said out loud."""
from datetime import date

import stockdata
from dashboard.v4 import company_data as C
from dashboard.v4 import company_ui as CU
from dashboard.v4 import home_data as H


def _rows():
    today = date.today().strftime("%d/%m/%Y")
    base = {"Date": today, "MA50": 95.0, "MA200": 90.0, "RSI14": 60.0, "Completeness": 100, "RiskLevel": "נמוך",
            "Support": 92.0, "Resistance": 110.0, "Price": 100.0, "_tier": "full", "Sector": "Healthcare",
            "ForwardPE": 20.0, "PEG": 0.9, "TargetMean": 95.0, "TargetLow": 70.0, "TargetHigh": 120.0, "AnalystCount": 20,
            "RevenueGrowth": 40.0, "OperatingMargin": 30.0, "DebtToEquity": 1.6, "FundDate": "29/10/2026"}
    return {
        "GOOD": {**base, "Ticker": "GOOD", "Name": "Good Corp", "ScoreV2": 86, "ContribFund": 32.5, "ContribTech": 22.0,
                 "ContribSector": 19.2, "ContribNews": 5.0, "ContribRisk": 7.3},
        "FAIR": {**base, "Ticker": "FAIR", "Name": "Fair Inc.", "ScoreV2": 60, "TargetMean": None, "TargetLow": None,
                 "TargetHigh": None, "AnalystCount": None},
        "TECH": {"Ticker": "TECH", "Price": 50.0, "MA200": 40.0, "MA50": 45.0, "Score": 70, "RiskLevel": "בינוני",
                 "_tier": "technical", "Date": today},
    }


PROF = {"_date": "2026-11-01", "target_mean": 104.0, "rev_growth": 39.0, "op_margin": 30.0, "debt_equity": 1.2,
        "fy_ends": ["31/12/2025", "31/12/2024", "31/12/2023"], "rev_hist": [90e9, 95e9, 80e9],
        "op_margin_hist": [30.0, 28.0, 25.0], "eps_hist": [5.0, 5.5, 4.0], "fcf_hist": [9e9, 9e9, 7e9],
        "pe_hist": [40.0, 45.0, 50.0], "trailing_pe": 30.0, "revenue": 100e9}


def test_the_decision_is_the_same_verdict_as_home_and_opportunities():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    for t in ("GOOD", "FAIR", "TECH"):
        dc = C.decision(vmap[t], rows[t])
        assert dc["label"] == vmap[t]["label"] and dc["tone"] == vmap[t]["tone"]
    card = H.picks(rows, vmap, limit=3)["cards"][0]
    assert card["ticker"] == "GOOD" and card["label"] == C.decision(vmap["GOOD"], rows["GOOD"])["label"]


def test_checks_are_the_live_gates_only():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    names = [c["name"] for c in C.checks(vmap["GOOD"], rows["GOOD"])]
    assert names == ["אמינות הנתונים", "איכות החברה", "מגמה", "סיכון"]          # price is not a gate
    fair = {c["name"]: c for c in C.checks(vmap["FAIR"], rows["FAIR"])}
    assert fair["איכות החברה"]["ok"] is False and fair["מגמה"]["ok"] is True


def test_quality_score_shows_its_momentum_share():
    parts = C.score_parts(_rows()["GOOD"])
    assert parts["total"] == 86 and parts["momentum_share"] == 48


def test_price_is_kept_apart_and_contradictions_are_explained():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    ps = C.price_section(vmap["GOOD"], rows["GOOD"], PROF)
    assert ps["analysts"]["gap"] == -5.0                                        # the scan's target, the verdict's basis
    assert any("מודדים דברים שונים" in c for c in ps["conflicts"])               # "attractive" yet above the target
    assert any("השתנה מאז הסריקה" in c for c in ps["conflicts"])                 # newer target listed, not swapped in
    html = CU.price(ps, advanced=True)
    assert "לא משנה את הערכת ההשקעה" in html
    assert "מחיר קנייה" not in html and "מחיר נוח" not in html                  # no invented buy price


def test_missing_targets_are_said_not_filled():
    rows = _rows()
    ps = C.price_section(stockdata.verdicts(rows)["FAIR"], rows["FAIR"], {})
    assert ps["analysts"] is None
    assert "לא זמינים" in CU.price(ps, advanced=False)


def test_a_stock_without_a_verdict_says_why():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    dc = C.decision(vmap["TECH"], rows["TECH"])
    assert dc["status"] == "nodata" and dc["answers"] == [] and dc["holder"] is None
    assert dc["why"].startswith("המניה לא נכללה היום בניתוח המלא")      # the reason first
    assert C.checks(vmap["TECH"], rows["TECH"]) == []                 # no "passing" rows beside "not enough data"
    assert CU.change_and_hold(dc) == ""


def test_business_history_is_oldest_first_and_flags_a_quarter_against_the_year():
    b = C.business(PROF, _rows()["GOOD"])
    assert [h["year"] for h in b["hist"]] == ["2023", "2024", "2025"]
    assert "רבעון" in b["lines"][0]["text"]                                      # Yahoo's growth is quarter on quarter
    assert "שונה מאוד מהשינוי השנתי" in b["note"]                               # +40% quarter, −5.3% last year


def test_newer_profile_values_are_listed_beside_the_scan():
    d = {x["key"]: x for x in C.diffs(_rows()["GOOD"], PROF)}
    assert d["TargetMean"]["scan"] == "$95.00" and d["TargetMean"]["newer"] == "$104.00"
    assert "DebtToEquity" in d and "OperatingMargin" not in d


def test_older_profile_never_overrides_the_verdicts_data():
    row = {**_rows()["GOOD"], "FundDate": "02/11/2026"}
    assert C.diffs(row, PROF) == []                                              # profile 01/11 is older
    assert C.diffs({**row, "FundDate": None}, PROF) == []                        # unknown date: say nothing


def test_a_verdict_on_old_business_data_is_flagged():
    row = {**_rows()["GOOD"], "Date": "30/10/2026", "FundDate": "25/10/2026"}
    note = H.stale_note(row)
    assert "25/10/2026" in note and "5 ימים" in note
    assert H.stale_note({**row, "FundDate": "30/10/2026"}) == ""
    assert H.stale_note({**row, "FundDate": None}) == ""


def test_the_price_tension_is_one_line_in_the_decision():
    rows = _rows()
    vmap = stockdata.verdicts(rows)
    ps = C.price_section(vmap["GOOD"], rows["GOOD"], PROF)
    assert ps["flag"] == "המחיר כבר גבוה ב-5% מהיעד הממוצע של האנליסטים."
    html = CU.hero(C.decision(vmap["GOOD"], rows["GOOD"]), "", ps["flag"])
    assert "לא משנה את הערכת ההשקעה" in html and 'href="#v4c-price"' in html


def test_distance_from_the_high_reads_the_right_way():
    """DistFromHigh% is (52-week high - price) / high: 0 at the high, positive below it."""
    assert C._below_high(0.0) == "בשיא" and C._below_high(0.3) == "בשיא"
    assert C._below_high(40.0) == "40.0% מתחת לשיא"
    assert C._below_high(None) == "—"


def test_the_gap_to_the_target_is_measured_from_the_right_base():
    def section(price, target):
        r = {**_rows()["GOOD"], "Price": price, "TargetMean": target}
        return C.price_section(stockdata.verdicts({"GOOD": r})["GOOD"], r, {})
    up = section(100.0, 150.0)
    assert up["analysts"]["plain"] == "היעד הממוצע של האנליסטים גבוה ב-50% מהמחיר."
    down = section(120.0, 100.0)
    assert down["analysts"]["plain"] == "המחיר גבוה ב-20% מהיעד הממוצע של האנליסטים."


def test_a_new_report_after_the_data_is_said_plainly():
    base = {**_rows()["GOOD"], "Date": "30/10/2026", "FundDate": "30/10/2026"}
    lag = {**base, "LastQuarter": "30/06/2026", "LastReport": "29/10/2026"}       # Yahoo not yet updated
    assert "עדיין של הרבעון שהסתיים ב-30/06/2026" in H.stale_note(lag)
    before = {**base, "FundDate": "28/10/2026", "LastQuarter": "30/06/2026", "LastReport": "05/08/2026"}
    assert H.stale_note({**before, "LastReport": "29/10/2026", "LastQuarter": "30/09/2026"}).startswith(
        "דוח כספי חדש פורסם ב-29/10/2026, וההערכה נשענת על נתונים עסקיים שנשלפו לפניו")
    current = {**base, "LastQuarter": "30/09/2026", "LastReport": "29/10/2026"}
    assert H.stale_note(current) == ""


def test_missing_inputs_are_unknown_not_failed():
    from dashboard.v4 import company_data as C
    cs = {c["name"]: c for c in C.checks({"quality": None, "reliability": {"score": None}, "trend": "unknown"}, {})}
    assert all(c["ok"] is None for c in cs.values())
