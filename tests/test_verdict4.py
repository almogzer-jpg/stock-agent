# -*- coding: utf-8 -*-
"""The four-dimension engine (shadow mode): quality from business data only, price
from several sources, one decision from an explicit table, always consistent."""
from datetime import date

import pandas as pd

import verdict4 as V4

TODAY = date.today().strftime("%d/%m/%Y")
ISO = date.today().isoformat()


def _row(**over):
    r = {"Ticker": "TST", "Date": TODAY, "Price": 100.0, "MA50": 95.0, "MA200": 90.0, "RSI14": 60.0,
         "Score": 70, "RiskLevel": "בינוני", "Support": 92.0, "Volatility": 25.0, "MaxDrawdown": -15.0, "Beta": 1.0}
    r.update(over)
    return r


def _profile(**over):
    """A solid industrial company priced reasonably."""
    p = {"sector": "Industrials", "industry": "Machinery", "roe": 24.0, "roa": 11.0, "op_margin": 26.0,
         "rev_growth": 12.0, "eps_growth": 15.0, "fcf": 2.2e9, "revenue": 10e9, "ebitda": 3e9,
         "total_debt": 3e9, "total_cash": 1e9, "debt_equity": 0.6, "book_value": 30.0,
         "fwd_pe": 18.0, "ev_ebitda": 12.0, "trailing_eps": 5.0, "peg": 1.2,
         "target_mean": 118.0, "analysts": 20, "price": 100.0,
         "rev_hist": [10e9, 9.2e9, 8.5e9, 7.9e9], "op_margin_hist": [26.0, 25.0, 24.5, 25.5],
         "eps_hist": [5.0, 4.4, 3.9, 3.5], "fcf_hist": [2.2e9, 2.0e9, 1.7e9, 1.5e9],
         "pe_hist": [22.0, 24.0, 21.0, 23.0], "_date": ISO}
    p.update(over)
    return p


def _peers(n=8, fpe=25.0, eve=16.0):
    """Industry peers that are all more expensive than the test company by default."""
    out = {f"P{i}": _profile(fwd_pe=fpe + i, ev_ebitda=eve + i) for i in range(n)}
    return out


def _decide(profile=None, row=None, peers=None, **kw):
    profile = _profile() if profile is None else profile
    universe = {**(peers if peers is not None else _peers()), "TST": profile}
    ctx = V4.context(universe)
    return V4.decide("TST", row or _row(), profile, ctx, **kw)


# ------------------------------------------------------------- quality
def test_quality_ignores_price_and_multiples():
    a = V4.quality(_profile())
    b = V4.quality(_profile(fwd_pe=60.0, ev_ebitda=45.0, peg=4.0, price=300.0, target_mean=150.0))
    assert a["score"] == b["score"] and a["tier"] == "strong"


def test_quality_needs_profitability_and_growth():
    q = V4.quality(_profile(op_margin=None, roe=None, roa=None))
    assert q["score"] is None and q["tier"] is None


def test_negative_equity_does_not_use_roe():
    q = V4.quality(_profile(book_value=-1.3, roe=None, roa=22.0))
    assert q["score"] is not None and q["pillars"]["profitability"] >= 75


def test_financials_skip_cash_and_balance_pillars():
    q = V4.quality(_profile(sector="Financial Services", op_margin=40.0, roe=18.0, roa=1.4, fcf=None, ebitda=None))
    assert "cash" not in q["pillars"] and "balance" not in q["pillars"] and q["score"] is not None


def test_weak_business_is_named():
    q = V4.quality(_profile(rev_growth=-8.0, op_margin=3.0, eps_growth=-20.0, roe=4.0, roa=1.5, fcf=-0.2e9,
                            rev_hist=[7e9, 7.5e9, 8e9, 8.5e9], eps_hist=[-0.5, 0.8, 1.2, 1.5],
                            fcf_hist=[-0.2e9, 0.1e9, 0.3e9, 0.4e9], op_margin_hist=[3.0, 9.0, 14.0, 22.0]))
    assert q["tier"] in ("weak", "poor")
    assert any("המכירות יורדות" in b for b in q["bad"])


# --------------------------------------------------------------- price
def test_price_uses_several_sources_with_reasons():
    pr = V4.price("TST", _profile(), V4.context({**_peers(), "TST": _profile()}))
    keys = {c["key"] for c in pr["components"]}
    assert keys == {"peers", "history", "growth", "analysts"}
    assert pr["label"] in ("attractive", "fair") and pr["basis"]


def test_one_source_is_not_enough():
    p = _profile(peg=None, target_mean=None, pe_hist=None, fwd_pe=None, ev_ebitda=None)
    pr = V4.price("TST", p, V4.context({"TST": p}))
    assert pr["label"] is None


def test_above_target_alone_cannot_make_price_attractive():
    # Expensive vs peers and vs its own history: only analysts could help, and they are below the price.
    p = _profile(fwd_pe=40.0, ev_ebitda=30.0, pe_hist=[15.0, 16.0, 14.0], peg=2.6, target_mean=95.0)
    pr = V4.price("TST", p, V4.context({**_peers(), "TST": p}))
    assert pr["upside"] < 0 and pr["label"] in ("full", "expensive")


def test_above_target_but_cheap_on_other_sources_says_so_explicitly():
    p = _profile(target_mean=97.0)                      # 3% above the consensus target
    pr = V4.price("TST", p, V4.context({**_peers(), "TST": p}))
    assert pr["upside"] < 0
    assert pr["label"] in ("attractive", "fair")
    assert "מעל יעד האנליסטים" in pr["justification"] and "ענף" in pr["justification"]


def test_attractive_needs_two_agreeing_sources():
    # Only the analysts are enthusiastic (+60% vs a typical +5%). History and PEG are neutral,
    # and the rest of the universe is in another sector, so there is no peer comparison.
    p = _profile(target_mean=160.0, pe_hist=[21.0, 21.0, 21.0], peg=1.6)
    others = {f"U{i}": _profile(sector="Utilities", industry="Utilities", target_mean=105.0) for i in range(8)}
    pr = V4.price("TST", p, V4.context({**others, "TST": p}))
    assert pr["score"] >= 65                                  # the blend alone would say "attractive"
    assert pr["label"] == "fair"


# ------------------------------------------------------------ decision
def test_strong_company_reasonable_price_uptrend_is_buy():
    v = _decide()
    assert v["action"] == "buy" and v["reason"] == "strong_good_price"
    assert V4.consistency(v) == []
    assert any("תמיכה" in c for c in v["conditions"])


def test_strong_company_full_price_waits_and_holder_keeps():
    p = _profile(fwd_pe=40.0, ev_ebitda=30.0, pe_hist=[15.0, 16.0, 14.0], peg=2.6, target_mean=95.0)
    v = _decide(p)
    assert v["action"] == "wait" and v["reason"] == "strong_full_price"
    assert v["holder"] == "hold" and "לא להגדיל" in v["holder_why"]
    assert v["conditions"] and all("$" in c or "ירידה" in c for c in v["conditions"])
    assert V4.consistency(v) == []


def test_entry_prices_are_below_todays_price():
    p = _profile(fwd_pe=40.0, ev_ebitda=30.0, pe_hist=[15.0, 16.0, 14.0], peg=2.6, target_mean=95.0)
    v = _decide(p)
    for c in v["conditions"]:
        if "$" in c:
            price = float(c.split("$")[1].split(" ")[0].split(")")[0].replace(",", ""))
            assert price < 100.0


def test_fair_company_waits_with_a_condition():
    p = _profile(op_margin=12.0, roe=10.0, rev_growth=4.0, eps_growth=2.0, fcf=0.6e9)
    v = _decide(p)
    assert v["dimensions"]["quality"]["tier"] in ("fair", "weak")
    assert v["action"] == "wait" and v["conditions"]


def test_downtrend_avoids_non_strong_and_waits_for_strong():
    weak = _decide(_profile(op_margin=12.0, roe=10.0, rev_growth=4.0, eps_growth=2.0, fcf=0.6e9),
                   row=_row(Price=80.0))
    assert weak["action"] == "avoid"
    strong = _decide(row=_row(Price=80.0))
    assert strong["action"] == "wait" and strong["reason"] == "strong_downtrend"


def test_very_high_risk_blocks_buy():
    v = _decide(row=_row(RiskLevel="גבוה מאוד"))
    assert v["action"] == "wait" and v["reason"] == "strong_very_high_risk"


def test_no_profile_is_nodata_never_a_guess():
    v = V4.decide("TST", _row(), None, V4.context({}))
    assert v["action"] == "nodata"


def test_momentum_does_not_change_quality():
    hot = _decide(row=_row(Score=100, RSI14=78.0))
    cold = _decide(row=_row(Score=20, Price=94.0))     # above MA200, below MA50
    assert hot["dimensions"]["quality"]["score"] == cold["dimensions"]["quality"]["score"]


def test_lly_case_strong_company_at_a_full_price():
    """01/11/2026: LLY trades ~1% above the consensus target of 29 analysts and far above
    its industry multiples, but below its own historical P/E. Strong business, full price."""
    lly = {"sector": "Healthcare", "industry": "Drug Manufacturers - General", "roe": 86.0, "roa": 21.1,
           "op_margin": 53.7, "rev_growth": 38.6, "eps_growth": 16.3, "fcf": 9.34e9, "revenue": 86.46e9,
           "ebitda": 46.49e9, "total_debt": 49.5e9, "total_cash": 4.89e9, "debt_equity": 1.23, "book_value": 45.19,
           "fwd_pe": 28.66, "ev_ebitda": 28.12, "trailing_eps": 30.81, "peg": 1.36, "target_mean": 1403.64,
           "analysts": 29, "price": 1417.54, "rev_hist": [65.18e9, 45.04e9, 34.12e9, 28.54e9],
           "op_margin_hist": [45.6, 37.8, 30.3, 29.0], "eps_hist": [22.95, 11.71, 5.8, 6.57],
           "fcf_hist": [5.96e9, 0.41e9, -3.15e9, 4.6e9], "pe_hist": [46.8, 65.9, 100.5, 55.7], "_date": ISO}
    peers = {f"PH{i}": {**lly, "fwd_pe": 12.0 + i, "ev_ebitda": 9.0 + i} for i in range(7)}
    row = _row(Price=1417.54, MA50=1193.68, MA200=1087.54, RSI14=74.5, Score=100, RiskLevel="נמוך",
               Support=1131.21)
    v = V4.decide("LLY", row, lly, V4.context({**peers, "LLY": lly}))
    assert v["dimensions"]["quality"]["tier"] == "strong"
    assert v["dimensions"]["price"]["key"] in ("full", "expensive")
    assert v["action"] == "wait" and v["reason"] == "strong_full_price"
    assert "יעד" in v["why"] and "מנגד" in v["why"]          # both sides of the price question
    assert v["holder"] == "hold"
    assert V4.consistency(v) == []


# ------------------------------------------------------ outcome measurement
def _se():
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "research"))
    import shadow_eval
    return shadow_eval


def _synthetic(n=300):
    """AAA rises 1%/day, BBB is flat, CCC falls hard then recovers. SPY drifts up."""
    days = pd.bdate_range("2025-01-06", periods=n)
    ccc = [100 * (0.98 ** i if i < 10 else 0.98 ** 10) for i in range(n)]
    closes = pd.DataFrame({"AAA": [100 * 1.01 ** i for i in range(n)], "BBB": [100.0] * n, "CCC": ccc,
                           "SPY": [100 * 1.002 ** i for i in range(n)]}, index=days)
    return days, closes


def _log(days, idx, rows):
    out = []
    for i in idx:
        for t, live, new, s in rows:
            out.append({"d": days[i].strftime("%d/%m/%Y"), "t": t, "s": s, "live": live, "new": new,
                        "p": "fair", "tm": "positive", "q": 75, "rel": 80, "pa": 2})
    log = pd.DataFrame(out)
    log["day"] = pd.to_datetime(log["d"], format="%d/%m/%Y")
    return log


def test_shadow_eval_measures_excess_drawdown_and_sector_neutral_return():
    SE = _se()
    days, closes = _synthetic()
    log = _log(days, [250], [("AAA", "wait", "buy", "Tech"), ("BBB", "buy", "wait", "Tech"),
                             ("CCC", "avoid", "avoid", "Energy")])
    r = SE.report(SE.outcomes(log, closes))[21]
    assert r["new"]["buy"]["excess_vs_avg_%"] > 0 > r["live"]["buy"]["excess_vs_avg_%"]
    assert r["new"]["buy"]["excess_vs_sector_%"] > 0                # beat its own sector too
    assert r["disagreements"]["new_buy_live_not"]["n"] == 1
    assert r["new"]["buy"]["enough_days"] is False                   # one day is never a conclusion
    assert "rising" in r["by_regime"]                                # SPY above its 200-day average
    assert set(r["by_sector"]) == {"Tech", "Energy"}


def test_shadow_eval_reports_drawdowns():
    SE = _se()
    days, closes = _synthetic()
    log = _log(days, [0], [("CCC", "buy", "avoid", "Energy"), ("AAA", "wait", "buy", "Tech")])
    r = SE.report(SE.outcomes(log, closes))[21]
    assert r["live"]["buy"]["avg_worst_drop_%"] < -15 and r["live"]["buy"]["share_fell_15%_%"] == 100.0
    assert r["new"]["buy"]["avg_worst_drop_%"] == 0


def test_stability_counts_changes_and_flips():
    SE = _se()
    days, _ = _synthetic(5)
    log = pd.concat([_log(days, [0], [("AAA", "buy", "buy", "Tech")]),
                     _log(days, [1], [("AAA", "avoid", "buy", "Tech")]),
                     _log(days, [2], [("AAA", "buy", "buy", "Tech")])])
    st = SE.stability(log)
    assert st["live"]["change_rate_%"] == 100.0 and st["live"]["buy_avoid_flips"] == 2
    assert st["new"]["change_rate_%"] == 0.0 and st["new"]["avg_buy_run_days"] == 3.0


def test_data_quality_per_day():
    SE = _se()
    days, _ = _synthetic(5)
    log = _log(days, [0], [("AAA", "nodata", "buy", "Tech"), ("BBB", "buy", "nodata", "Tech")])
    dq = SE.data_quality(log)[0]
    assert dq["new_nodata_%"] == 50.0 and dq["live_nodata_%"] == 50.0 and dq["avg_profile_age_days"] == 2.0


def test_headline_never_concludes_without_matured_decisions():
    SE = _se()
    lines = SE.headline({"log_days": 1, "results": "no matured decisions yet"})
    assert "אין מה להסיק" in lines[-1]
