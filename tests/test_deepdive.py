# -*- coding: utf-8 -*-
"""Company Deep Dive (Phase 18) — pure rule-based helpers (no network)."""
import deepdive as dd


def test_valuation_class_bands():
    assert "בחסר" in dd.valuation_class(80, 1.0, 18)
    assert "הוגן" in dd.valuation_class(50, 1.5, 25)
    assert "ביוקר" in dd.valuation_class(20, 3.0, 60)
    assert dd.valuation_class(None, None, None) == dd.NA


def test_recommendation_levels_and_caps():
    assert dd.recommendation(80, "נמוך", 70, 75).startswith("Strong Buy")
    assert dd.recommendation(70, "נמוך", 60, 70).startswith("Buy")
    assert dd.recommendation(50, "בינוני", 50, 60).startswith("Hold")
    assert dd.recommendation(40, "בינוני", 50, 60).startswith("Reduce")
    assert dd.recommendation(20, "גבוה", 30, 50).startswith("Avoid")
    # very-high risk caps a Strong Buy down
    capped = dd.recommendation(80, "גבוה מאוד", 70, 75)
    assert not capped.startswith("Strong Buy")
    # low trust caps enthusiasm
    assert not dd.recommendation(80, "נמוך", 70, 20).startswith("Strong Buy")


def test_scenario_probs():
    hi = dd.scenario_probs(80)
    assert hi["bull"] > hi["bear"] and sum(hi.values()) == 100
    lo = dd.scenario_probs(20)
    assert lo["bear"] > lo["bull"] and sum(lo.values()) == 100
    mid = dd.scenario_probs(50)
    assert mid["bull"] == mid["bear"] and sum(mid.values()) == 100


def test_build_thesis_has_three_cases():
    ctx = {"score_v2": 72, "valuation_label": "מתומחר בהוגן", "risk_cat": "בינוני",
           "rev_growth": 18.0, "eps_growth": 22.0, "op_margin": 25.0, "trend": "מגמת עלייה",
           "beta": 1.1, "maxdd": -18.0}
    th = dd.build_thesis(ctx)
    assert th["bull"] and th["base"] and th["bear"]
    assert "18" in th["bull"]            # real number woven in


def test_build_pros_cons_exactly_five_each():
    ctx = {"fund": 80, "rev_growth": 20.0, "op_margin": 28.0, "trend": "מגמת עלייה",
           "risk_cat": "גבוה מאוד", "beta": 1.6, "maxdd": -40.0, "valuation": 30,
           "trust": 35}
    pc = dd.build_pros_cons(ctx)
    assert len(pc["pros"]) == 5 and len(pc["cons"]) == 5


def test_growth_trend_and_profiles():
    assert dd._growth_trend(25, 30) == "מאיץ"
    assert dd._growth_trend(-5, -3) == "מתכווץ"
    assert dd._growth_trend(None, None) == dd.NA
    assert "אגרסיבי" in dd._investor_profile("גבוה מאוד", 60)
    assert "שמרני" in dd._investor_profile("נמוך", 18)


def _rep(**over):
    """Synthetic analyze() report for the decision engine (pure, no network)."""
    rep = {
        "raw_metrics": {"price": 100.0, "rev_growth": 20.0, "eps_growth": 30.0,
                        "op_margin": 25.0, "fcf_growth": 12.0, "debt_equity": 0.4,
                        "roic": 18.0, "ret_3m": 12.0, "ret_1m": 4.0, "rsi": 60.0},
        "scores": {"final_v2": {"value": 76}, "fundamental": {"value": 80},
                   "technical": {"value": 70}, "valuation": {"value": 55},
                   "sector": {"value": 70}, "trust": {"value": 68},
                   "news": {"value": 50}, "risk": {"value": 30}},
        "technicals": {"trend": "מגמת עלייה", "sub_scores": {"momentum": 65},
                       "sr_levels": {"price": 100.0, "support": 97.5, "resistance": 112.0,
                                     "dist_support_pct": -2.5, "dist_resistance_pct": 12.0,
                                     "risk_reward": 4.8, "status": "normal"}},
        "risk": {"beta": 1.1, "max_drawdown": -18.0, "risk_score": 30, "category": "בינוני"},
        "opinion": {"recommendation": "Buy · קנייה"},
        "scenarios": [{"key": "base", "target": {"price": "$118", "price_num": 118.0, "upside": 18.0}}],
        "pros_cons": {"pros": ["צמיחה גבוהה", "—"], "cons": ["תמחור מתוח"]},
        "regulation_risks": {"sector_risks": ["רגולציה", "תחרות"]},
    }
    rep.update(over)
    return rep


def test_decision_core_numbers():
    d = dd.investment_decision(_rep(), regime_score=80)
    assert d["price"] == 100.0 and d["target_num"] == 118.0
    assert d["upside"] == 18.0 and d["downside"] == -2.5
    assert abs(d["margin_of_safety"] - round((118 - 100) / 118 * 100, 1)) < 0.01
    assert d["rr"] == round(18.0 / 2.5, 2)             # target-upside / support-downside
    assert d["rr_interpretation"] == "מצוין"           # ≥2.5
    assert d["score_v2"] == 76 and d["confidence"] == 68


def test_decision_entry_quality_bands():
    d = dd.investment_decision(_rep())
    assert d["entry"]["band"] == "excellent"           # 2.5% over support, RR 4.8
    ext = dd.investment_decision(_rep(technicals={
        "trend": "מגמת עלייה", "sub_scores": {"momentum": 65},
        "sr_levels": {"price": 100.0, "support": 90.0, "resistance": 101.5,
                      "dist_support_pct": -10.0, "dist_resistance_pct": 1.5,
                      "risk_reward": 0.15, "status": "normal"}}))
    assert ext["entry"]["band"] == "extended"          # 1.5% below resistance
    dn = dd.investment_decision(_rep(technicals={
        "trend": "מגמת ירידה", "sub_scores": {}, "sr_levels": {}}))
    assert dn["entry"]["band"] == "avoid"


def test_decision_checklist_and_missing_data():
    d = dd.investment_decision(_rep(), regime_score=None)
    ch = {name: status for name, _v, status, _s in d["checklist"]}
    assert ch["צמיחה"] == "good" and ch["חוב"] == "good" and ch["תמחור"] == "neutral"
    assert ch["סביבת מאקרו"] == "na"                   # no regime → not enough data
    bare = dd.investment_decision({"scores": {}, "technicals": {}, "risk": {},
                                   "opinion": {}, "scenarios": [], "raw_metrics": {}})
    assert bare["margin_of_safety"] is None and bare["rr"] is None
    assert bare["target"] == dd.NA and bare["risk_level"] == dd.NOT_ENOUGH


def test_decision_wait_for_and_risks_data_driven():
    d = dd.investment_decision(_rep())
    assert any("תנאי-סף" in w or "פריצה" in w or "תמחור" in w for w in d["wait_for"])
    exp = dd.investment_decision(_rep(scores={"final_v2": {"value": 60}, "fundamental": {"value": 70},
                                              "technical": {"value": 60}, "valuation": {"value": 20},
                                              "sector": {"value": 30}, "trust": {"value": 30},
                                              "news": {"value": 50}, "risk": {"value": 70}}))
    assert any("תמחור" in r for r in exp["risks"])     # expensive → valuation risk listed
    assert any("סקטור" in r for r in exp["risks"])     # weak sector risk listed
    assert any("תמחור" in w for w in exp["wait_for"])  # waiting condition matches weakness


def test_money_and_pct_formatting():
    assert dd._money(2.5e12) == "$2.50T"
    assert dd._money(None) == dd.NA
    assert dd._pct(3.456) == "+3.46%"
    assert dd._pct(None) == dd.NA


def test_decision_breakdown_and_blockers():
    r = _rep()
    r["scores"]["final_v2"]["contributions"] = {"fundamental": 28.0, "technical": 17.5,
                                                "sector": 13.0, "news": 5.0, "risk": 7.0}
    d = dd.investment_decision(r)
    bd = d["breakdown"]
    assert bd["contributions"][0]["name"] == "פונדמנטלי"        # sorted by contribution
    assert bd["contributions"][0]["points"] == 28.0
    # valuation 55 is not <55 → no blocker; drop it low → blocker appears
    r["scores"]["valuation"]["value"] = 20
    bd2 = dd.investment_decision(r)["breakdown"]
    assert any("תמחור" in b for b in bd2["blockers"])


def test_engine_v2_thesis_confidence_and_position():
    d = dd.investment_decision(_rep(), regime_score=80)
    tc = d["thesis_confidence"]
    assert 0 <= tc["score"] <= 100 and tc["label"] in ("גבוה", "בינוני", "נמוך")
    assert set(tc["parts"]) == {"הסכמת אותות", "אימות היסטורי", "התאמה למשטר השוק", "עומק ראיות"}
    # aligned dims (all ~70-80) + regime aligned → decent confidence
    assert tc["score"] >= 60
    pos = d["position"]
    assert pos["name"] and pos["range"]
    # negative recommendation → no position
    d2 = dd.investment_decision(_rep(opinion={"recommendation": "Avoid · להימנע"}))
    assert d2["position"]["range"] == "0%"


def test_engine_v2_invalidators_catalysts_summary():
    r = _rep()
    r["raw_metrics"]["earnings_date"] = "30/07/2026"
    d = dd.investment_decision(r, regime_score=80)
    assert any("תמיכה" in x for x in d["invalidators"])          # measurable kill-condition
    assert any("guidance" in x or "תחזית" in x for x in d["invalidators"])
    cats = d["catalysts"]
    assert any("דוח כספי" in c["event"] and c["date"] == "30/07/2026" for c in cats)
    es = d["exec_summary_3"]
    assert len(es) == 3 and all(isinstance(s, str) and len(s) > 20 for s in es)


def test_engine_v2_rating_change_explanation():
    hist = [{"date": "01/07/2026", "recommendation": "Watch · מעקב", "confidence": 60,
             "score_v2": 62, "target": 100.0, "risk": "בינוני"},
            {"date": "13/07/2026", "recommendation": "Buy · קנייה", "confidence": 75,
             "score_v2": 74, "target": 118.0, "risk": "נמוך"}]
    d = dd.investment_decision(_rep(history=hist))
    rc = d["rating_change"]
    assert rc and rc["from"].startswith("Watch") and rc["to"].startswith("Buy")
    assert any("ציון V2" in x for x in rc["reasons"])
    # unchanged recommendation → no explanation needed
    hist2 = [dict(hist[1], date="12/07/2026"), hist[1]]
    assert dd.investment_decision(_rep(history=hist2))["rating_change"] is None


def test_engine_v2_checklist_extended():
    d = dd.investment_decision(_rep(raw_metrics={**_rep()["raw_metrics"],
                                                 "inst_held_pct": 72.0}))
    names = [c[0] for c in d["checklist"]]
    assert any("איכות רווחים" in n for n in names)
    assert any("אחזקות מוסדיות" in n for n in names)
    ch = {c[0]: c[2] for c in d["checklist"]}
    assert ch["אחזקות מוסדיות"] == "good"                        # 72% ≥ 60
