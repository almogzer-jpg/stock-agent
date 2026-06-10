# -*- coding: utf-8 -*-
"""Technical indicators: moving averages, RSI, volume, 52-week metrics."""
import pandas as pd

from config import DATE_FMT


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing (the standard RSI).

    Returns a Series aligned with `close`; the first `period` values are NaN.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)          # positive moves only
    loss = -delta.clip(upper=0.0)         # magnitude of negative moves

    # Wilder's smoothing == EMA with alpha = 1/period.
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))
    # No losses over the window -> RSI is 100 by definition.
    return out.where(avg_loss != 0, 100.0)


def compute_indicators(df: pd.DataFrame) -> dict | None:
    """Compute the full metric set for the latest trading day.

    Returns a dict of metrics, or None if there isn't enough history
    (a meaningful 200-day MA needs at least 200 rows).
    """
    if df is None or len(df) < 200:
        return None

    close = df["Close"]
    volume = df["Volume"]

    price = float(close.iloc[-1])

    # Moving averages
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1])
    ma200 = float(close.rolling(200).mean().iloc[-1])

    # RSI(14)
    rsi14 = float(rsi(close, 14).iloc[-1])

    # Volume metrics
    avg_vol20 = float(volume.rolling(20).mean().iloc[-1])
    cur_vol = float(volume.iloc[-1])
    vol_ratio = cur_vol / avg_vol20 if avg_vol20 > 0 else 0.0

    # 52-week high and how far below it we are (0% = at the high)
    high_52w = float(close.tail(252).max())
    dist_from_high = (high_52w - price) / high_52w * 100.0 if high_52w > 0 else 0.0

    return {
        "Date": df.index[-1].strftime(DATE_FMT),   # DD/MM/YYYY (Israeli format)
        "Price": round(price, 2),
        "MA20": round(ma20, 2),
        "MA50": round(ma50, 2),
        "MA200": round(ma200, 2),
        "RSI14": round(rsi14, 1),
        "AvgVol20": int(avg_vol20),
        "CurVol": int(cur_vol),
        "VolRatio": round(vol_ratio, 2),
        "High52w": round(high_52w, 2),
        "DistFromHigh%": round(dist_from_high, 2),
    }
