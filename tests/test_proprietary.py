# -*- coding: utf-8 -*-
"""Proprietary indicators: breadth, fear&greed, capital flow, upside, confidence."""
from conftest import base_metrics
import proprietary


def test_market_breadth(scan_df):
    b = proprietary.market_breadth(scan_df)
    assert 0 <= b["score"] <= 100
    assert 0 <= b["above50"] <= 100
    assert b["advancers"] + b["decliners"] <= len(scan_df)
    assert b["method"]


def test_fear_greed_range_and_label(scan_df):
    fg = proprietary.fear_greed(scan_df, vix=18.0)
    assert 0 <= fg["score"] <= 100
    assert fg["label"] in ("פחד קיצוני", "פחד", "ניטרלי", "חמדנות", "חמדנות קיצונית")
    assert fg["method"]


def test_fear_greed_low_vix_more_greedy(scan_df):
    calm = proprietary.fear_greed(scan_df, vix=12.0)
    panic = proprietary.fear_greed(scan_df, vix=34.0)
    assert calm["score"] >= panic["score"]


def test_capital_flow_ranks_by_score():
    sectors = [{"sector": "A", "score": 90, "change_pct": 1, "rs": 5},
               {"sector": "B", "score": 40, "change_pct": 0, "rs": 0},
               {"sector": "C", "score": 10, "change_pct": -2, "rs": -5}]
    flow = proprietary.capital_flow(sectors)
    assert flow["inflows"][0]["sector"] == "A"
    assert flow["outflows"][0]["sector"] == "C"


def test_expected_upside_range():
    up = proprietary.expected_upside(base_metrics({"DistFromHigh%": 12.0}))
    assert 0 <= up["pct"] <= 60
    assert up["method"]


def test_confidence_range_and_factors(strong):
    c = proprietary.confidence(strong, backtest_hit=80.0)
    assert 0 <= c["score"] <= 100
    assert c["level"] in ("נמוך", "בינוני", "גבוה")
    assert c["factors"] and c["method"]


def test_confidence_strong_beats_weak(strong, weak):
    assert proprietary.confidence(strong, 80)["score"] > proprietary.confidence(weak, 20)["score"]
