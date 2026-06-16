# -*- coding: utf-8 -*-
"""Technical toolkit (Phase 18) — pure functions over synthetic price frames."""
import numpy as np
import pandas as pd

import technicals as ta


def _frame(n=300, start=100.0, drift=0.4, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = start + np.cumsum(drift + rng.normal(0, 0.5, n))
    close = np.maximum(close, 1.0)
    high = close + np.abs(rng.normal(0, 0.6, n))
    low = close - np.abs(rng.normal(0, 0.6, n))
    vol = rng.integers(1_000_000, 3_000_000, n).astype(float)
    return pd.DataFrame({"Close": close, "High": high, "Low": low, "Volume": vol}, index=idx)


def test_moving_averages_and_flags():
    df = _frame()
    ma = ta.moving_averages(df["Close"])
    assert ma["ma20"] is not None and ma["ma200"] is not None
    assert isinstance(ma["above_ma50"], bool)
    # uptrend: price should be above the 200-MA
    assert ma["above_ma200"] is True


def test_returns_windows_and_ytd():
    df = _frame()
    r = ta.returns(df["Close"])
    for k in ("1w", "1m", "3m", "6m", "1y"):
        assert r[k] is not None
    assert r["ytd"] is not None          # DatetimeIndex present


def test_macd_and_atr():
    df = _frame()
    m = ta.macd(df["Close"])
    assert m["macd"] is not None and m["signal"] is not None and m["hist"] is not None
    assert ta.atr(df) is not None


def test_support_resistance_real_levels():
    df = _frame()
    sr = ta.support_resistance(df)
    price = float(df["Close"].iloc[-1])
    if sr["support"] is not None:
        assert sr["support"] < price          # support below price
    if sr["resistance"] is not None:
        assert sr["resistance"] > price        # resistance above price


def test_trend_and_momentum_classification():
    up = _frame(drift=0.6, seed=2)
    ma = ta.moving_averages(up["Close"])
    tr = ta.returns(up["Close"])
    cls = ta.trend_class(ma["price"], ma["ma50"], ma["ma200"], tr["3m"])
    assert "עלייה" in cls
    down = _frame(n=300, start=600.0, drift=-0.9, seed=3)
    mad = ta.moving_averages(down["Close"])
    trd = ta.returns(down["Close"])
    assert "ירידה" in ta.trend_class(mad["price"], mad["ma50"], mad["ma200"], trd["3m"])
    assert ta.momentum_class(70, 0.5, 4) == "חזק"
    assert ta.momentum_class(35, -0.5, -3) == "חלש"
    assert ta.momentum_class(50, 0, 0) == "ניטרלי"


def test_sub_scores_bounded():
    m = {"Price": 120, "MA20": 115, "MA50": 110, "MA200": 100,
         "RSI14": 60, "DistFromHigh%": 4, "VolRatio": 1.4}
    s = ta.sub_scores(m, vol_annual=28, ret_3m=12)
    for k in ("trend", "momentum", "volume", "volatility"):
        assert 0 <= s[k] <= 100


def test_insufficient_history_returns_none():
    short = _frame(n=15)
    assert ta.macd(short["Close"])["macd"] is None
    assert ta.cross_signal(short["Close"]) is None
