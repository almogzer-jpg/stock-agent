# -*- coding: utf-8 -*-
"""Shared free-data loader (yfinance / Yahoo Finance). No paid APIs.

Every module that needs price history goes through load_ohlcv() so the data
source can be swapped in one place.
"""
try:
    import yfinance as yf
except ImportError:
    raise SystemExit(
        "Missing dependency 'yfinance'. Run: pip install -r requirements.txt"
    )

from config import HISTORY_PERIOD


def load_ohlcv(symbol: str, period: str = HISTORY_PERIOD):
    """Return split/dividend-adjusted daily OHLCV for `symbol`, or None.

    The most recent row includes today's (possibly partial) candle while the
    US market is open, so downstream metrics reflect the current trading day.
    Returns None on any download failure or empty result — callers skip it.
    """
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
    except Exception as exc:  # network / bad-symbol errors shouldn't kill the run
        print(f"  ! {symbol}: download failed ({exc})")
        return None
    if df is None or df.empty:
        return None
    # Drop rows with no Close (e.g. an incomplete/NaN candle at the start of a
    # new trading day) so the latest row is always a real, valid session.
    df = df[df["Close"].notna()]
    return df if not df.empty else None
