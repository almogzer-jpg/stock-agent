# -*- coding: utf-8 -*-
"""Ranking engine: score breakdown, normalization, classification."""
from conftest import base_metrics
from ranking_engine.score import score_stock, score_breakdown, WEIGHTS
from ranking_engine.interpret import classify
from scanners.breakout import is_breakout


def test_score_in_range(strong, weak):
    for m in (strong, weak):
        assert 0 <= score_stock(m) <= 100


def test_breakdown_sums_to_score(strong, weak):
    for m in (strong, weak):
        assert abs(sum(score_breakdown(m).values()) - score_stock(m)) <= 0.6


def test_breakdown_components_within_weights(strong):
    bd = score_breakdown(strong)
    for key, weight in WEIGHTS.items():
        assert 0 <= bd[key] <= weight + 0.01


def test_strong_scores_higher_than_weak(strong, weak):
    assert score_stock(strong) > score_stock(weak)


def test_strong_is_positive_weak_is_avoid(strong, weak):
    assert classify(strong)["group"] == "positive"
    assert classify(weak)["group"] == "avoid"


def test_classify_returns_required_fields(strong):
    info = classify(strong)
    for k in ("group", "emoji", "label", "color", "summary", "detail"):
        assert k in info and info[k]


def test_breakout_detection():
    m = base_metrics()  # strong + volume 1.6 + near high + RSI 60
    assert is_breakout(m) is True
    no_vol = base_metrics({"VolRatio": 1.0})
    assert is_breakout(no_vol) is False
    below_ma = base_metrics({"Price": 80.0, "MA200": 100.0})
    assert is_breakout(below_ma) is False


def test_overbought_rsi_not_full_score():
    overbought = base_metrics({"RSI14": 85.0})
    healthy = base_metrics({"RSI14": 60.0})
    assert score_stock(overbought) < score_stock(healthy)
