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

import statistics

from indicators.technical import rsi
from config import NEAR_HIGH_PCT, VOLUME_SPIKE, RSI_MIN, RSI_MAX


def _signal_series(df):
    """Boolean breakout-signal series over the full history."""
    close = df["Close"]
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    avg_vol = df["Volume"].rolling(20).mean()
    r = rsi(close, 14)
    dist = (close.rolling(252).max() - close) / close.rolling(252).max() * 100
    return ((close > ma50) & (close > ma200) & (dist <= NEAR_HIGH_PCT)
            & (df["Volume"] >= VOLUME_SPIKE * avg_vol)
            & (r >= RSI_MIN) & (r <= RSI_MAX)), ma50


def _agg(trades: list) -> dict:
    """Aggregate a list of trade dicts into summary stats."""
    if not trades:
        return {"occurrences": 0, "win_rate": None, "avg_return": None}
    rets = [t["ret"] for t in trades]
    brels = [t["brel"] for t in trades if t["brel"] is not None]
    return {
        "occurrences": len(trades),
        "win_rate": round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1),
        "avg_return": round(statistics.mean(rets), 2),
        "median_return": round(statistics.median(rets), 2),
        "max_drawdown": round(min(t["dd"] for t in trades), 2),
        "benchmark_rel": round(statistics.mean(brels), 2) if brels else None,
        "avg_holding": round(statistics.mean(t["hold"] for t in trades), 1),
    }


def backtest_signal(df, market_close=None, max_hold: int = 20) -> dict | None:
    """Institutional backtest of the breakout signal on one ticker.

    Simulates non-overlapping trades: enter on signal, exit on a close below the
    50-day MA (trend break) or after `max_hold` days. Reports win rate, average/
    median return, worst-trade drawdown, benchmark-relative return, occurrences,
    average holding period, and an in-sample / out-of-sample split (70/30) for
    validation. Returns None if there isn't enough history.
    """
    if df is None or len(df) < 260:
        return None
    signal, ma50 = _signal_series(df)
    close = df["Close"]
    idx = close.index
    prices = close.values
    ma50v = ma50.values
    sig = signal.fillna(False).values
    n = len(prices)
    mkt = market_close.dropna() if market_close is not None else None

    trades = []
    pos = 0
    while pos < n - 1:
        if not sig[pos]:
            pos += 1
            continue
        entry = prices[pos]
        low_track = entry
        exit_pos = None
        for k in range(pos + 1, min(pos + max_hold + 1, n)):
            low_track = min(low_track, prices[k])
            if prices[k] < ma50v[k]:          # trend-break exit
                exit_pos = k
                break
        if exit_pos is None:
            exit_pos = min(pos + max_hold, n - 1)
        ret = (prices[exit_pos] / entry - 1) * 100
        dd = (low_track / entry - 1) * 100
        brel = None
        if mkt is not None:
            try:
                me, mx = mkt.asof(idx[pos]), mkt.asof(idx[exit_pos])
                if me and mx and me == me and mx == mx:
                    brel = ret - (mx / me - 1) * 100
            except Exception:
                pass
        trades.append({"ret": ret, "dd": dd, "hold": exit_pos - pos, "brel": brel})
        pos = exit_pos + 1                     # non-overlapping

    out = _agg(trades)
    if out["occurrences"] == 0:
        out.update({"oos_win_rate": None, "oos_avg_return": None, "confidence": "נמוך"})
        return out

    # Out-of-sample: validate on the most recent 30% of trades.
    split = int(len(trades) * 0.7)
    is_t, oos_t = trades[:split], trades[split:]
    oos = _agg(oos_t)
    out["is_win_rate"] = _agg(is_t).get("win_rate")
    out["oos_win_rate"] = oos.get("win_rate")
    out["oos_avg_return"] = oos.get("avg_return")

    # Confidence: sample size + win rate + OOS agreement.
    occ, wr = out["occurrences"], out["win_rate"]
    oos_wr = out["oos_win_rate"]
    if occ >= 8 and wr >= 60 and (oos_wr is None or oos_wr >= 50):
        out["confidence"] = "גבוה"
    elif occ >= 4 and wr >= 50:
        out["confidence"] = "בינוני"
    else:
        out["confidence"] = "נמוך"
    return out


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
