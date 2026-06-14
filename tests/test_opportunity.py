# -*- coding: utf-8 -*-
"""Opportunity Hunter: explanations + grouping are based on real signals."""
from conftest import base_metrics
from explain import explain
from ranking_engine.interpret import classify


def test_explain_returns_all_sections(strong):
    ex = explain(strong)
    for k in ("why_buy", "why_watch", "why_avoid", "catalysts", "risks", "group"):
        assert k in ex
    assert isinstance(ex["why_buy"], list)


def test_strong_has_buy_reasons(strong):
    ex = explain(strong)
    assert ex["group"] == "positive"
    assert any("ממוצע 200" in x for x in ex["why_buy"])


def test_weak_has_avoid_reasons(weak):
    ex = explain(weak)
    assert ex["group"] == "avoid"
    assert ex["why_avoid"] and "אין" not in ex["why_avoid"][0]


def test_breakout_is_a_catalyst(strong):
    ex = explain(strong)            # strong fixture is a breakout
    assert any("פריצה" in c for c in ex["catalysts"])


def test_earnings_event_becomes_catalyst_and_risk():
    m = base_metrics()
    ex = explain(m, events={"days_to_earnings": 3, "earnings_date": "2026-06-13"})
    assert any("דוחות" in c for c in ex["catalysts"])
    assert any("דוחות" in r for r in ex["risks"])


def test_no_empty_sections(strong, weak):
    for m in (strong, weak):
        ex = explain(m)
        assert ex["catalysts"] and ex["risks"]   # fallbacks guarantee non-empty


def test_opportunities_have_real_signal(scan_df):
    # Every 'positive' row must be above the 200-day MA or a breakout.
    for _, r in scan_df.iterrows():
        if classify(r)["group"] == "positive":
            assert r["Price"] > r["MA200"] or r["Breakout"]
