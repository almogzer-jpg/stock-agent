# -*- coding: utf-8 -*-
"""Portfolio Decision Engine: allocation targets, actions, constraints."""
import decisions


def test_valuation_score():
    cheap = decisions.valuation_score({"PEG": 0.8, "ForwardPE": 15})
    rich = decisions.valuation_score({"PEG": 4, "ForwardPE": 55})
    assert cheap > rich
    assert decisions.valuation_score({}) is None


def test_target_allocation_by_score():
    assert decisions.target_allocation(80, "בינוני", 70, "שורי") == 15
    assert decisions.target_allocation(45, "בינוני", 70, "שורי") == 2
    assert decisions.target_allocation(20, "בינוני", 70, "שורי") == 0


def test_risk_caps_allocation():
    # Strong score but very-high risk caps the size at 5%.
    assert decisions.target_allocation(85, "גבוה מאוד", 70, "שורי") == 5


def test_risk_off_reduces_allocation():
    on = decisions.target_allocation(80, "בינוני", 70, "שורי")
    off = decisions.target_allocation(80, "בינוני", 70, "דובי (Risk-Off)")
    assert off < on


def test_decide_actions():
    over = {"ticker": "X", "weight": 30, "score_v2": 70, "risk_level": "בינוני", "sector_score": 80}
    d = decisions.decide_holding(over, "שורי")
    assert d["action"] == "Reduce"          # 30% > 15% target
    assert d["priority"] == "גבוהה"          # >20% violates constraint
    exit_ = decisions.decide_holding({"ticker": "Y", "weight": 5, "score_v2": 20,
                                      "risk_level": "גבוה", "sector_score": 30}, "שורי")
    assert exit_["action"] == "Exit"


def test_portfolio_decisions_constraints_and_today():
    positions = [
        {"ticker": "A", "weight": 30, "score_v2": 70, "risk_level": "בינוני",
         "sector": "Technology", "sector_score": 30},
        {"ticker": "B", "weight": 10, "score_v2": 55, "risk_level": "נמוך",
         "sector": "Technology", "sector_score": 30},
    ]
    out = decisions.portfolio_decisions(positions, [], "שורי",
                                        {"weighted_beta": 1.3}, {"high_pairs": []})
    assert out["holdings"] and out["today"]
    assert any(">" in c and "20%" in c for c in out["constraints"])     # single position
    assert any("ביתא" in c for c in out["constraints"])                 # beta > 1.2
    assert out["risk_actions"]                                          # beta-driven
