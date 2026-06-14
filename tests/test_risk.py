# -*- coding: utf-8 -*-
"""Risk Intelligence Engine: beta, volatility, drawdown, score, correlation."""
import numpy as np
import pandas as pd
import risk


def _series(returns, start=100.0):
    prices = [start]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return pd.Series(prices, index=pd.date_range("2024-01-01", periods=len(prices), freq="D"))


def test_beta_recovers_known_slope():
    rng = np.random.default_rng(0)
    mr = rng.normal(0, 0.012, 300)
    m, s = _series(mr), _series(1.5 * mr)        # stock = 1.5× market
    assert 1.4 <= risk.beta(s, m) <= 1.6


def test_volatility_positive_and_scales():
    rng = np.random.default_rng(1)
    low = risk.volatility(_series(rng.normal(0, 0.005, 300)))
    high = risk.volatility(_series(rng.normal(0, 0.03, 300)))
    assert 0 < low < high


def test_max_drawdown():
    s = pd.Series(list(np.linspace(100, 150, 20)) + list(np.linspace(150, 75, 20)),
                  index=pd.date_range("2024-01-01", periods=40, freq="D"))
    mdd = risk.max_drawdown(s)
    assert mdd is not None and -55 <= mdd <= -45     # 75/150 - 1 = -50%


def test_risk_score_and_category_ordering():
    low = risk.risk_score(vol=18, bta=0.8, mdd=-12)
    high = risk.risk_score(vol=60, bta=1.8, mdd=-55)
    assert 0 <= low <= 100 and 0 <= high <= 100 and high > low
    assert risk.category(low) == "נמוך"
    assert risk.category(high) in ("גבוה", "גבוה מאוד")


def test_risk_profile_keys_and_warnings():
    rng = np.random.default_rng(2)
    mr = rng.normal(0, 0.02, 300)
    rp = risk.risk_profile(_series(2.0 * mr), _series(mr))   # high beta/vol
    for k in ("beta", "volatility", "max_drawdown", "risk_score", "category", "warnings"):
        assert k in rp
    assert isinstance(rp["warnings"], list)


def test_correlation_finds_high_pair():
    rng = np.random.default_rng(3)
    base = rng.normal(0, 0.01, 300)
    a = _series(base)
    b = _series(base + rng.normal(0, 0.0004, 300))     # ~ correlated with A
    c = _series(rng.normal(0, 0.01, 300))              # independent
    res = risk.correlation_pairs({"A": a, "B": b, "C": c}, threshold=0.7)
    assert any({p["a"], p["b"]} == {"A", "B"} for p in res["high_pairs"])


def test_portfolio_risk():
    positions = [{"ticker": "A", "weight": 60}, {"ticker": "B", "weight": 40}]
    pr = risk.portfolio_risk(positions, {"A": 1.5, "B": 0.8}, {"A": 40, "B": 20}, {"Tech": 100})
    assert pr["weighted_beta"] == round(0.6 * 1.5 + 0.4 * 0.8, 2)
    assert 0 <= pr["concentration_risk"] <= 100
    assert any("סקטור" in w or "פוזיציה" in w for w in pr["warnings"])
