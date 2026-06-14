# -*- coding: utf-8 -*-
"""Indicators (RSI / compute_indicators), sector mapping, news sentiment."""
import market
from indicators.technical import rsi, compute_indicators
from news.sentiment import score_headlines


def test_rsi_in_range(price_df):
    r = rsi(price_df["Close"], 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_compute_indicators_keys_and_no_nan(price_df):
    m = compute_indicators(price_df)
    assert m is not None
    for k in ("Price", "MA20", "MA50", "MA200", "RSI14", "VolRatio", "DistFromHigh%"):
        assert k in m and m[k] == m[k]          # not NaN


def test_compute_indicators_needs_history():
    import pandas as pd
    short = pd.DataFrame({"Close": [1, 2, 3], "Volume": [1, 1, 1]})
    assert compute_indicators(short) is None


def test_sector_score_mapping():
    sectors = [{"sector": "טכנולוגיה", "score": 91},
               {"sector": "פיננסים", "score": 53}]
    assert market.sector_score_for("Technology", sectors) == 91
    assert market.sector_score_for("Financial Services", sectors) == 53
    assert market.sector_score_for("Unknown Sector", sectors) is None


def test_news_sentiment():
    pos = score_headlines([{"title": "Stock surges on record profit and upgrade"}])
    neg = score_headlines([{"title": "Shares plunge on lawsuit and downgrade fears"}])
    assert pos["score"] > 50 and neg["score"] < 50
    assert score_headlines([])["score"] == 50      # no news -> neutral, not NaN
