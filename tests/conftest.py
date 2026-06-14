# -*- coding: utf-8 -*-
"""Shared pytest fixtures. Tests are PURE (no network) — synthetic inputs only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from ranking_engine.score import score_stock
from scanners.breakout import is_breakout


def base_metrics(over=None):
    """A complete metrics dict (a strong/healthy stock by default).

    Pass `over` as a dict to override (keys like 'DistFromHigh%' can't be kwargs).
    """
    m = {
        "Ticker": "TST", "Name": "Test Co",
        "Price": 110.0, "MA20": 105.0, "MA50": 100.0, "MA200": 90.0,
        "RSI14": 60.0, "AvgVol20": 1_000_000, "CurVol": 1_600_000,
        "VolRatio": 1.6, "High52w": 112.0, "DistFromHigh%": 1.8,
        "DailyChange%": 1.2, "ScoreSentiment": 70.0, "ScoreRisk": 30.0,
        "ScoreFundamental": 70.0, "RiskLevel": "בינוני",
    }
    if over:
        m.update(over)
    m["Breakout"] = is_breakout(m)
    m["Score"] = score_stock(m)
    return m


@pytest.fixture
def strong():
    return base_metrics()


@pytest.fixture
def weak():
    return base_metrics({"Price": 80.0, "MA20": 85.0, "MA50": 95.0, "MA200": 100.0,
                         "RSI14": 35.0, "VolRatio": 0.6, "High52w": 130.0,
                         "DistFromHigh%": 38.0, "DailyChange%": -1.5,
                         "RiskLevel": "גבוה", "ScoreRisk": 75.0})


@pytest.fixture
def scan_df():
    rows = [
        base_metrics({"Ticker": "AAA"}),
        base_metrics({"Ticker": "BBB", "Price": 80.0, "MA50": 95.0, "MA200": 100.0,
                      "RSI14": 35.0, "VolRatio": 0.6, "DistFromHigh%": 38.0,
                      "DailyChange%": -1.5, "RiskLevel": "גבוה"}),
        base_metrics({"Ticker": "CCC", "RSI14": 45.0, "VolRatio": 1.0,
                      "DistFromHigh%": 8.0, "DailyChange%": 0.3}),
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def price_df():
    """Synthetic 300-day OHLCV with a gentle uptrend (for indicators)."""
    idx = pd.date_range("2025-01-01", periods=300, freq="D")
    close = pd.Series(100 + 0.1 * np.arange(300) + 2 * np.sin(np.arange(300) / 10), index=idx)
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99,
                         "Close": close, "Volume": pd.Series([1_000_000] * 300, index=idx)})
