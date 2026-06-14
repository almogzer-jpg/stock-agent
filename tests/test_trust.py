# -*- coding: utf-8 -*-
"""Trust & Validation engine: trust score, factors, signal reliability."""
import trust


def _row(**kw):
    base = {"Score": 70, "ScoreFundamental": 75, "ScoreSentiment": 68, "Completeness": 100,
            "Beta": 1.0, "Volatility": 25, "MaxDrawdown": -15, "Confidence": 70,
            "RevenueGrowth": 15, "EPSGrowth": 20, "FCFGrowth": 10, "OperatingMargin": 25,
            "DebtToEquity": 0.5, "ROIC": 20, "PEG": 1.2, "ForwardPE": 20}
    base.update(kw)
    return base


def test_trust_score_range_and_factor_sum():
    ti = trust.trust_score(_row(), {"occurrences": 10, "win_rate": 65, "oos_win_rate": 60})
    assert 0 <= ti["score"] <= 100
    assert ti["category"] in ("נמוך", "בינוני", "גבוה")
    assert abs(sum(ti["factors"].values()) - ti["score"]) <= 1
    assert ti["strengths"] and ti["limitations"]


def test_strong_validation_beats_weak():
    good = trust.trust_score(_row(), {"occurrences": 12, "win_rate": 70, "oos_win_rate": 65})
    poor = trust.trust_score(_row(), {"occurrences": 2, "win_rate": 30, "oos_win_rate": None})
    assert good["score"] > poor["score"]
    assert good["category"] == "גבוה"


def test_missing_fundamentals_flagged():
    row = _row(ScoreFundamental=None)
    for f in trust.FUND_FIELDS:
        row[f] = None
    ti = trust.trust_score(row, {"occurrences": 0})
    assert any("פונדמנט" in lim for lim in ti["limitations"])
    assert ti["score"] < 80


def test_signal_reliability():
    sr = trust.signal_reliability(_row(Confidence=80),
                                  {"win_rate": 62, "occurrences": 9,
                                   "avg_return": 3.1, "benchmark_rel": 1.5, "max_drawdown": -8})
    assert sr["category"] == "גבוה"
    assert sr["hist_win_rate"] == 62 and sr["excess_return"] == 1.5 and sr["occurrences"] == 9
