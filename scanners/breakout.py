# -*- coding: utf-8 -*-
"""Breakout setup scanner.

A momentum setup: a stock in an uptrend, near its 52-week high, pushing higher
on above-average volume with healthy (not yet overbought) RSI.
"""
from config import NEAR_HIGH_PCT, VOLUME_SPIKE, RSI_MIN, RSI_MAX


def is_breakout(m: dict) -> bool:
    """Return True only if all five breakout conditions hold."""
    return (
        m["Price"] > m["MA50"]                       # above 50-day MA
        and m["Price"] > m["MA200"]                  # above 200-day MA
        and m["DistFromHigh%"] <= NEAR_HIGH_PCT      # within 10% of 52w high
        and m["VolRatio"] >= VOLUME_SPIKE            # volume >= 1.5x average
        and RSI_MIN <= m["RSI14"] <= RSI_MAX         # RSI in the 50-75 band
    )
