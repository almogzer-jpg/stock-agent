# -*- coding: utf-8 -*-
"""Universe + scanner pure logic (no network)."""
import numpy as np
import pandas as pd
import scanner
import universe


def test_ticker_normalization():
    assert universe._norm("brk.b") == "BRK-B"
    assert universe._norm(" aapl ") == "AAPL"


def test_metrics_structure():
    n = 300
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(100, 150, n) + np.sin(np.arange(n) / 7) * 2, index=idx)
    vol = pd.Series([1_000_000] * n, index=idx)
    m = scanner._metrics(close, vol)
    assert m is not None
    for k in ("Price", "MA20", "MA50", "MA200", "RSI14", "VolRatio",
              "DistFromHigh%", "Ret1m", "Ret3m"):
        assert k in m
    assert isinstance(m["_reclaim"], bool)


def test_metrics_short_history_returns_none():
    assert scanner._metrics(pd.Series([1, 2, 3]), pd.Series([1, 1, 1])) is None
