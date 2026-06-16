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


def test_money_and_pct_formatting():
    assert dd._money(2.5e12) == "$2.50T"
    assert dd._money(None) == dd.NA
    assert dd._pct(3.456) == "+3.46%"
    assert dd._pct(None) == dd.NA
