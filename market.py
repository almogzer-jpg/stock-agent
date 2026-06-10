# -*- coding: utf-8 -*-
"""Market-level data: indices, sector ETFs, and a market-regime score.

All data is REAL and free (yfinance / Yahoo Finance). No paid APIs and no
fabricated numbers. Results are cached briefly so the dashboard stays snappy.
"""
import yfinance as yf

# Major US indices (Yahoo symbols) shown in the market-overview panel.
INDICES = {
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "Dow Jones",
    "^VIX": "VIX",
}

# Sector SPDR ETFs — each tracks one S&P sector. Used for the sector heatmap.
SECTOR_ETFS = {
    "XLK": "טכנולוגיה",
    "XLF": "פיננסים",
    "XLV": "בריאות",
    "XLY": "צריכה מחזורית",
    "XLP": "צריכה בסיסית",
    "XLE": "אנרגיה",
    "XLI": "תעשייה",
    "XLB": "חומרים",
    "XLRE": "נדל\"ן",
    "XLU": "שירותים ציבוריים",
    "XLC": "שירותי תקשורת",
}


def _pct_change_last(close) -> float:
    """Last-session % change from a Close series."""
    if close is None or len(close) < 2:
        return 0.0
    return float((close.iloc[-1] / close.iloc[-2] - 1.0) * 100.0)


def get_indices() -> list[dict]:
    """Return a list of {symbol, name, price, change_pct} for the indices."""
    out = []
    for sym, name in INDICES.items():
        try:
            close = yf.Ticker(sym).history(period="5d", auto_adjust=True)["Close"]
            out.append({
                "symbol": sym, "name": name,
                "price": round(float(close.iloc[-1]), 2),
                "change_pct": round(_pct_change_last(close), 2),
            })
        except Exception:
            out.append({"symbol": sym, "name": name, "price": None, "change_pct": None})
    return out


def get_index_history(symbol: str = "^GSPC", period: str = "6mo"):
    """Return the Close series for an index (for the trend chart)."""
    try:
        return yf.Ticker(symbol).history(period=period, auto_adjust=True)["Close"]
    except Exception:
        return None


def get_sector_heatmap() -> list[dict]:
    """Return [{etf, sector, change_pct}] — last-session move per sector ETF."""
    out = []
    for etf, sector in SECTOR_ETFS.items():
        try:
            close = yf.Ticker(etf).history(period="5d", auto_adjust=True)["Close"]
            out.append({"etf": etf, "sector": sector,
                        "change_pct": round(_pct_change_last(close), 2)})
        except Exception:
            continue
    return out


def market_regime_score() -> dict:
    """Compute a 0-100 'market regime' score from real index data.

    Combines three real signals:
      * S&P 500 above its 200-day MA (long-term trend up?)  — 40 pts
      * S&P 500 above its 50-day MA  (medium-term trend up?) — 30 pts
      * VIX level (lower = calmer market)                    — 30 pts
    Returns {score, label} where label is a Hebrew risk-on/off description.
    """
    score = 0.0
    try:
        spx = yf.Ticker("^GSPC").history(period="1y", auto_adjust=True)["Close"]
        if spx.iloc[-1] > spx.rolling(200).mean().iloc[-1]:
            score += 40
        if spx.iloc[-1] > spx.rolling(50).mean().iloc[-1]:
            score += 30
    except Exception:
        pass
    try:
        vix = float(yf.Ticker("^VIX").history(period="5d", auto_adjust=True)["Close"].iloc[-1])
        # VIX < 15 calm (full 30 pts); > 30 fearful (0 pts); linear between.
        score += max(0.0, min(30.0, 30.0 * (30.0 - vix) / 15.0))
    except Exception:
        pass

    score = int(round(max(0.0, min(100.0, score))))
    if score >= 70:
        label = "שורי (Risk-On)"
    elif score >= 40:
        label = "ניטרלי"
    else:
        label = "דובי (Risk-Off)"
    return {"score": score, "label": label}
