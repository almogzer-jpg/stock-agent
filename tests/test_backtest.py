# -*- coding: utf-8 -*-
"""Institutional backtester: aggregation math + signal backtest structure."""
import numpy as np
import pandas as pd
from backtesting import backtester


def test_agg_math():
    trades = [{"ret": 5, "dd": -3, "hold": 4, "brel": 2},
              {"ret": -2, "dd": -6, "hold": 8, "brel": -1},
              {"ret": 10, "dd": -1, "hold": 3, "brel": 7}]
    a = backtester._agg(trades)
    assert a["occurrences"] == 3
    assert a["win_rate"] == round(2 / 3 * 100, 1)        # 66.7
    assert a["avg_return"] == round((5 - 2 + 10) / 3, 2)
    assert a["median_return"] == 5
    assert a["max_drawdown"] == -6                        # worst single-trade drawdown
    assert a["benchmark_rel"] == round((2 - 1 + 7) / 3, 2)
    assert a["avg_holding"] == round((4 + 8 + 3) / 3, 1)


def test_agg_empty():
    a = backtester._agg([])
    assert a["occurrences"] == 0 and a["win_rate"] is None


def test_backtest_signal_structure():
    n = 400
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(100, 200, n) + np.sin(np.arange(n) / 8) * 3, index=idx)
    vol = pd.Series(1_000_000 * (1 + 0.7 * (np.arange(n) % 9 == 0)), index=idx)
    df = pd.DataFrame({"Close": close, "Volume": vol})
    res = backtester.backtest_signal(df)
    assert res is not None
    for k in ("occurrences", "win_rate", "avg_return", "confidence"):
        assert k in res
    assert res["confidence"] in ("נמוך", "בינוני", "גבוה")
    if res["occurrences"] > 0:
        assert 0 <= res["win_rate"] <= 100
        assert res["avg_holding"] > 0


def test_backtest_signal_insufficient_history():
    df = pd.DataFrame({"Close": [1, 2, 3], "Volume": [1, 1, 1]})
    assert backtester.backtest_signal(df) is None
