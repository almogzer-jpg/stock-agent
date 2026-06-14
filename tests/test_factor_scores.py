# -*- coding: utf-8 -*-
"""Factor sub-scores: technical, fundamental, sentiment, risk."""
from conftest import base_metrics
from ranking_engine.factor_scores import (factor_scores, fundamental_score,
                                           sentiment_score, risk_score)

GOOD_FUND = {"RevenueGrowth": 25, "EPSGrowth": 30, "FCFGrowth": 15,
             "OperatingMargin": 30, "DebtToEquity": 0.3, "ROIC": 25,
             "PEG": 0.9, "ForwardPE": 18}
BAD_FUND = {"RevenueGrowth": -10, "EPSGrowth": -20, "FCFGrowth": -30,
            "OperatingMargin": -5, "DebtToEquity": 3.5, "ROIC": -2,
            "PEG": 5, "ForwardPE": 60}


def test_factor_scores_ranges(strong):
    fs = factor_scores(strong, closes=[100, 101, 102, 101, 103] * 6,
                       fundamentals=GOOD_FUND, news_sent={"score": 70})
    assert 0 <= fs["technical"] <= 100
    assert 0 <= fs["fundamental"] <= 100
    assert 0 <= fs["sentiment"] <= 100
    assert 0 <= fs["risk"] <= 100
    assert fs["risk_level"] in ("נמוך", "בינוני", "גבוה")


def test_fundamental_score_good_beats_bad():
    assert fundamental_score(GOOD_FUND) > fundamental_score(BAD_FUND)


def test_fundamental_none_when_no_data():
    assert fundamental_score({}) is None
    assert fundamental_score(None) is None


def test_fundamental_score_in_range():
    assert 0 <= fundamental_score(GOOD_FUND) <= 100
    assert 0 <= fundamental_score(BAD_FUND) <= 100


def test_sentiment_higher_for_uptrend(strong, weak):
    assert sentiment_score(strong) > sentiment_score(weak)


def test_risk_higher_for_volatile_below_ma(weak):
    volatile = [100, 80, 120, 70, 130, 60, 140] * 5
    score, level = risk_score(weak, closes=volatile)
    assert 0 <= score <= 100
    assert level in ("נמוך", "בינוני", "גבוה")


def test_news_score_passthrough(strong):
    fs = factor_scores(strong, closes=None, fundamentals=None, news_sent={"score": 88})
    assert fs["news"] == 88
    assert fs["fundamental"] is None        # no fundamentals -> None (not fabricated)
