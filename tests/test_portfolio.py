# -*- coding: utf-8 -*-
"""Portfolio analytics: P/L, weights, exposures, health, alerts."""
import portfolio

POSITIONS = [
    {"ticker": "AAA", "name": "A", "quantity": 10, "avg_cost": 100, "price": 150,
     "daily_change_pct": 1.0, "ret_1m": 5.0, "ret_ytd": 10.0,
     "sector": "Technology", "market_cap": 3e12, "risk_level": "בינוני",
     "score": 80, "status_group": "positive"},
    {"ticker": "BBB", "name": "B", "quantity": 5, "avg_cost": 200, "price": 180,
     "daily_change_pct": -2.0, "ret_1m": -3.0, "ret_ytd": -8.0,
     "sector": "Technology", "market_cap": 1.5e9, "risk_level": "גבוה",
     "score": 20, "status_group": "avoid"},
]
BENCH = {"daily": 0.5, "ret_1m": 3.0, "ret_ytd": 8.0}


def test_build_portfolio_totals():
    pf = portfolio.build_portfolio(POSITIONS, BENCH)
    # MV = 10*150 + 5*180 = 1500 + 900 = 2400 ; cost = 1000 + 1000 = 2000
    assert pf["total_value"] == 2400
    assert pf["total_cost"] == 2000
    assert pf["total_pl"] == 400
    assert abs((pf["total_value"] - pf["total_cost"]) - pf["total_pl"]) < 1e-6


def test_weights_sum_to_100():
    pf = portfolio.build_portfolio(POSITIONS, BENCH)
    assert abs(sum(p["weight"] for p in pf["positions"]) - 100) < 0.5


def test_exposures_sum_to_100():
    pf = portfolio.build_portfolio(POSITIONS, BENCH)
    for key in ("sector", "risk", "cap"):
        assert abs(sum(pf["exposures"][key].values()) - 100) < 0.5


def test_pl_pct_per_position():
    pf = portfolio.build_portfolio(POSITIONS, BENCH)
    aaa = next(p for p in pf["positions"] if p["ticker"] == "AAA")
    assert abs(aaa["pl_pct"] - 50.0) < 0.01           # 150/100 - 1


def test_health_in_range_and_alerts():
    pf = portfolio.build_portfolio(POSITIONS, BENCH)
    assert 0 <= pf["health"]["score"] <= 100
    # Tech is 100% of a 2-name book -> sector-concentration alert expected
    assert any("סקטור" in a["message"] or "Technology" in a["message"] for a in pf["alerts"])
    # BBB is 'avoid' -> deterioration alert expected
    assert any(a["scope"] == "BBB" for a in pf["alerts"])


def test_empty_portfolio():
    assert portfolio.build_portfolio([], BENCH).get("empty") is True


def test_cap_bucket():
    pf = portfolio.build_portfolio(POSITIONS, BENCH)
    buckets = {p["ticker"]: p["cap_bucket"] for p in pf["positions"]}
    assert buckets["AAA"] == "Large Cap"      # 3T
    assert buckets["BBB"] == "Small Cap"      # 1.5B
