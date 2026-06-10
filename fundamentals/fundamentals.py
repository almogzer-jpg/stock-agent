# -*- coding: utf-8 -*-
"""Free fundamental snapshot via yfinance. No paid APIs."""
try:
    import yfinance as yf
except ImportError:
    yf = None


def get_fundamentals(symbol: str) -> dict:
    """Return a small dict of fundamental fields for `symbol`.

    Best-effort: returns {} on any failure. Fields come from yfinance's .info,
    which is slower and occasionally rate-limited (hence the config flag).
    """
    if yf is None:
        return {}
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        return {}

    def g(key):
        v = info.get(key)
        return v if v is not None else ""

    return {
        "MarketCap": g("marketCap"),
        "TrailingPE": g("trailingPE"),
        "ForwardPE": g("forwardPE"),
        "ProfitMargin": g("profitMargins"),
        "RevenueGrowth": g("revenueGrowth"),
        "Sector": g("sector"),
    }
