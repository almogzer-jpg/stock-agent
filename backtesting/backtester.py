# -*- coding: utf-8 -*-
"""Minimal breakout backtester (free data).

For each historical day where the breakout setup was true, measure the N-day
forward return, then report how often it was positive (hit-rate) and the
average return. This is an MVP stub — extend with stops, costs, and sizing.

Run standalone:
    python backtesting/backtester.py AAPL MSFT
"""
import os
import sys

# Make the package root importable when run directly as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.technical import rsi
from config import NEAR_HIGH_PCT, VOLUME_SPIKE, RSI_MIN, RSI_MAX


def backtest_symbol(df, horizon: int = 10) -> dict | None:
    """Backtest the breakout signal on one ticker's history.

    Returns {signals, hit_rate, avg_return_pct, horizon}, or None if there
    isn't enough history. hit_rate / avg_return are None when no signal fired.
    """
    # Need a year for the rolling windows plus the forward horizon.
    if df is None or len(df) < 252 + horizon:
        return None

    close = df["Close"]
    volume = df["Volume"]

    # Vectorised versions of the same metrics indicators/ computes per-day.
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    avg_vol20 = volume.rolling(20).mean()
    rsi14 = rsi(close, 14)
    high_52w = close.rolling(252).max()
    dist = (high_52w - close) / high_52w * 100.0

    # The breakout condition as a boolean Series over all of history.
    signal = (
        (close > ma50)
        & (close > ma200)
        & (dist <= NEAR_HIGH_PCT)
        & (volume >= VOLUME_SPIKE * avg_vol20)
        & (rsi14 >= RSI_MIN)
        & (rsi14 <= RSI_MAX)
    )

    # Forward return over `horizon` trading days.
    fwd = close.shift(-horizon) / close - 1.0
    sig_returns = fwd[signal].dropna()

    n = int(len(sig_returns))
    if n == 0:
        return {"signals": 0, "hit_rate": None, "avg_return_pct": None,
                "horizon": horizon}
    return {
        "signals": n,
        "hit_rate": round(float((sig_returns > 0).mean()) * 100, 1),
        "avg_return_pct": round(float(sig_returns.mean()) * 100, 2),
        "horizon": horizon,
    }


if __name__ == "__main__":
    # Tiny CLI so the backtester is usable on its own.
    from data_loader import load_ohlcv

    symbols = [s.upper() for s in sys.argv[1:]] or ["AAPL"]
    print(f"Backtesting breakout signal (forward horizon = 10 trading days)\n")
    for sym in symbols:
        res = backtest_symbol(load_ohlcv(sym))
        if not res:
            print(f"  {sym:<6} not enough data")
        elif res["signals"] == 0:
            print(f"  {sym:<6} no breakout signals in history")
        else:
            print(f"  {sym:<6} signals={res['signals']:<4} "
                  f"hit-rate={res['hit_rate']}%  "
                  f"avg {res['horizon']}d return={res['avg_return_pct']}%")
