# -*- coding: utf-8 -*-
"""The unified verdict engine: one answer per stock, explained, never guessed."""
from datetime import date

import pandas as pd

import stockdata
import verdict as V

TODAY = date.today().strftime("%d/%m/%Y")


def _row(**over):
    r = {"Ticker": "TST", "Name": "Test Corp", "Date": TODAY, "Price": 100.0, "MA50": 95.0,
         "MA200": 90.0, "RSI14": 60.0, "ScoreV2": 74, "ScoreFundamental": 75, "Score": 70,
         "Completeness": 100, "RiskLevel": "בינוני", "Support": 92.0, "Resistance": 110.0,
         "DistSupport%": -8.0, "DistResistance%": 10.0, "RiskReward": 1.25,
         "RevenueGrowth": 18.0, "OperatingMargin": 25.0, "ROIC": 20.0, "DebtToEquity": 0.3}
    r.update(over)
    return r


def test_strong_company_in_uptrend_is_buy_with_specific_reason():
    v = V.verdict_for_row(_row())
    assert v["action"] == "buy" and v["emoji"] == "🟢"
    assert "המכירות גדלות" in v["why"]                # specific, not boilerplate
    assert v["holder"] == "hold"
    assert v["reliability"]["label"] == "גבוהה"
    assert any("תמיכה" in c for c in v["conditions"])  # what would cancel it


def test_downtrend_blocks_buy_for_non_strong_and_waits_for_strong():
    weak = V.verdict_for_row(_row(Price=80.0, ScoreV2=60))
    assert weak["action"] == "avoid"
    assert any("200" in c for c in weak["conditions"])
    strong = V.verdict_for_row(_row(Price=80.0, ScoreV2=80))
    assert strong["action"] == "wait"


def test_poor_quality_is_avoid_and_holder_reviews():
    v = V.verdict_for_row(_row(ScoreV2=40))
    assert v["action"] == "avoid" and v["holder"] == "review_sell"


def test_fair_quality_waits_with_condition():
    v = V.verdict_for_row(_row(ScoreV2=60))
    assert v["action"] == "wait" and v["conditions"]


def test_unenriched_scan_row_never_gets_a_verdict():
    # universe rows without fundamentals carry ScoreV2 == technical score
    r = _row(Name=None, ScoreFundamental=None, Completeness=None)
    v = V.verdict_for_row(r)
    assert v["action"] == "nodata" and v["quality"] is None


def test_stale_or_partial_data_lowers_reliability():
    fresh = V.verdict_for_row(_row())["reliability"]["score"]
    stale = V.verdict_for_row(_row(Date="01/01/2020"))["reliability"]["score"]
    partial = V.verdict_for_row(_row(Completeness=55))["reliability"]["score"]
    assert stale < fresh and partial < fresh


def test_unvalidated_timing_rules_do_not_change_the_verdict():
    # The historical study found no benefit from these "wait" rules.
    assert not any(r["active"] for r in V.TIMING_EVIDENCE.values())
    hot = V.verdict_for_row({**_row(), "RSI14": 82.0, "DistResistance%": 1.0, "RiskReward": 0.1})
    assert hot["action"] == "buy"
    assert any("תנודות" in c for c in hot["cons"])       # disclosed as risk, not a gate


def test_price_above_analyst_target_is_disclosed():
    v = V.verdict_for_row(_row(TargetMean=90.0))
    assert any("ממחיר היעד" in c for c in v["cons"])
    assert v["levels"]["upside"] == -10.0


def test_earnings_soon_is_the_first_caution():
    v = V.verdict_for_row(_row(DaysToEarnings=0))
    assert v["cons"][0].startswith("דוחות כספיים היום")


def test_canonical_rows_prefer_full_watchlist_row():
    res = pd.DataFrame([_row(Ticker="AAA", ScoreV2=80)])
    uni = {"all": [{"Ticker": "AAA", "ScoreV2": 55, "Score": 55}, {"Ticker": "BBB", "ScoreV2": 70}],
           "opportunities": [{"Ticker": "AAA", "Name": "A", "ScoreV2": 60, "ScoreFundamental": 50}]}
    rows = stockdata.load_rows(res, uni, {"AAA": {"days_to_earnings": 3}})
    assert rows["AAA"]["_tier"] == "full" and rows["AAA"]["ScoreV2"] == 80
    assert rows["AAA"]["DaysToEarnings"] == 3
    assert rows["BBB"]["_tier"] == "technical"
    vm = stockdata.verdicts(rows)
    assert vm["BBB"]["action"] == "nodata"
    assert [v["ticker"] for v in stockdata.ranked(vm, rows)] == ["AAA"]   # technical-only excluded


def test_same_inputs_same_verdict_everywhere():
    """Daily row and a live report built from the same numbers must agree."""
    row = _row()
    rep = {"ticker": "TST", "overview": {"name": "Test Corp"},
           "raw_metrics": {"price": 100.0, "rsi": 60.0, "ret_3m": 5.0, "rev_growth": 18.0,
                           "op_margin": 25.0, "roic": 20.0, "debt_equity": 0.3},
           "scores": {"final_v2": {"value": 74}, "fundamental": {"value": 75}},
           "technicals": {"moving_averages": {"ma50": 95.0, "ma200": 90.0},
                          "sr_levels": {"support": 92.0, "resistance": 110.0, "dist_support_pct": -8.0,
                                        "dist_resistance_pct": 10.0, "risk_reward": 1.25}},
           "risk": {"category": "בינוני"}, "meta": {"completeness": 1.0}, "quality_warnings": []}
    assert V.verdict_for_row(row)["action"] == V.verdict_for_report(rep)["action"] == "buy"


def test_evidence_only_with_large_sample():
    ev = V.evidence_for(V.features_from_row(_row()))
    if ev:                                    # research results committed with the repo
        assert ev["n"] >= 300 and ev["p10_return"] < 0


def test_quality_price_and_buy_now_are_separate_answers():
    # a cheap stock is not automatically a buy: weak company in a downtrend
    cheap_weak = V.verdict_for_row(_row(ScoreV2=50, Price=80.0, PEG=0.8, ForwardPE=12))
    f = cheap_weak["facets"]
    assert f["price"]["label"] == "מחיר אטרקטיבי"
    assert f["quality"]["label"] == "חברה חלשה" and f["now"]["label"] == "לא עכשיו"
    # a strong company can be a consider-buy even when expensive, and says so
    pricey = V.verdict_for_row(_row(ScoreV2=75, PEG=2.8, ForwardPE=36))
    assert pricey["facets"]["quality"]["label"] == "חברה חזקה"
    assert pricey["facets"]["price"]["label"] == "מחיר גבוה"
    assert pricey["action"] == "buy" and any("יקרה" in c for c in pricey["cons"])
    # no valuation inputs and no analyst target: say so, never guess
    unknown = V.verdict_for_row(_row())
    assert unknown["facets"]["price"]["label"] == "אין מספיק מידע"
