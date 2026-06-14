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
    "^RUT": "Russell 2000",
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


# Map yfinance English sector names -> our Hebrew sector names (for per-stock
# sector scores). Used by the dashboard's score-transparency view.
SECTOR_EN_TO_HE = {
    "Technology": "טכנולוגיה",
    "Financial Services": "פיננסים",
    "Healthcare": "בריאות",
    "Consumer Cyclical": "צריכה מחזורית",
    "Consumer Defensive": "צריכה בסיסית",
    "Energy": "אנרגיה",
    "Industrials": "תעשייה",
    "Basic Materials": "חומרים",
    "Real Estate": "נדל\"ן",
    "Utilities": "שירותים ציבוריים",
    "Communication Services": "שירותי תקשורת",
}


def sector_score_for(english_sector, sectors: list):
    """Return the Sector Score for a stock's (English) sector, or None."""
    he = SECTOR_EN_TO_HE.get(english_sector)
    if not he or not sectors:
        return None
    for s in sectors:
        if s.get("sector") == he:
            return s.get("score")
    return None


def _pct_change_last(close):
    """Last-session % change from a Close series, or None if not computable.

    Drops NaN rows first (a new trading day can yield an incomplete candle),
    so we never return or propagate NaN.
    """
    if close is None:
        return None
    close = close.dropna()
    if len(close) < 2:
        return None
    return float((close.iloc[-1] / close.iloc[-2] - 1.0) * 100.0)


def get_indices() -> list[dict]:
    """Return a list of {symbol, name, price, change_pct} for the indices.

    price/change_pct are None (never NaN) when the data isn't available.
    """
    out = []
    for sym, name in INDICES.items():
        price, cp = None, None
        try:
            close = yf.Ticker(sym).history(period="5d", auto_adjust=True)["Close"].dropna()
            if len(close):
                price = round(float(close.iloc[-1]), 2)
            cp = _pct_change_last(close)
        except Exception:
            pass
        out.append({"symbol": sym, "name": name, "price": price,
                    "change_pct": round(cp, 2) if cp is not None else None})
    return out


def get_index_history(symbol: str = "^GSPC", period: str = "6mo"):
    """Return the (NaN-free) Close series for an index, or None."""
    try:
        close = yf.Ticker(symbol).history(period=period, auto_adjust=True)["Close"].dropna()
        return close if len(close) else None
    except Exception:
        return None


def get_sector_heatmap() -> list[dict]:
    """Return [{etf, sector, change_pct}] — last-session move per sector ETF.

    Only sectors with a valid (non-None) move are included.
    """
    out = []
    for etf, sector in SECTOR_ETFS.items():
        try:
            close = yf.Ticker(etf).history(period="5d", auto_adjust=True)["Close"].dropna()
            cp = _pct_change_last(close)
            if cp is not None:
                out.append({"etf": etf, "sector": sector, "change_pct": round(cp, 2)})
        except Exception:
            continue
    return out


def _ret(series, days):
    """% return over `days` trading sessions, or None."""
    s = series.dropna()
    if len(s) <= days:
        return None
    return float((s.iloc[-1] / s.iloc[-1 - days] - 1.0) * 100.0)


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def sector_intelligence() -> list[dict]:
    """Per-sector analysis from real sector-ETF data (one batched download).

    For each sector ETF computes: daily move, 1m/3m return, relative strength
    vs the S&P 500 (1m), trend (vs 50/200-day MAs), a 0-100 momentum gauge, and
    a composite 0-100 Sector Score. Returns the list ranked by score (rank 1 =
    strongest). All real data — sector ETF performance is the standard proxy.
    """
    syms = list(SECTOR_ETFS) + ["^GSPC"]
    try:
        data = yf.download(syms, period="1y", auto_adjust=True, progress=False)["Close"]
    except Exception:
        return []
    if data is None or data.empty or "^GSPC" not in data:
        return []

    spx_1m = _ret(data["^GSPC"], 21) or 0.0

    rows = []
    for etf, name in SECTOR_ETFS.items():
        if etf not in data:
            continue
        s = data[etf].dropna()
        if len(s) < 60:
            continue
        price = float(s.iloc[-1])
        ma50 = float(s.rolling(50).mean().iloc[-1]) if len(s) >= 50 else price
        ma200 = float(s.rolling(200).mean().iloc[-1]) if len(s) >= 200 else ma50
        daily = _ret(s, 1) or 0.0
        ret_1m = _ret(s, 21) or 0.0
        ret_3m = _ret(s, 63) or 0.0
        rs_1m = ret_1m - spx_1m                      # relative strength vs S&P

        # Trend (vs moving averages)
        if price > ma50 > ma200:
            trend, trend_pts = "עולה", 40
        elif price > ma50:
            trend, trend_pts = "מתחזק", 25
        elif price < ma50 < ma200:
            trend, trend_pts = "יורד", 0
        else:
            trend, trend_pts = "מעורב", 15

        # Momentum gauge 0-100 (from 1-month return, -10%..+15%)
        momentum = round(_clamp((ret_1m + 10) / 25 * 100), 0)
        mom_pts = momentum / 100 * 30
        # Relative-strength points 0-30 (rs -8%..+8%)
        rs_pts = _clamp((rs_1m + 8) / 16 * 30, 0, 30)

        score = int(round(_clamp(trend_pts + mom_pts + rs_pts)))
        rows.append({
            "sector": name, "etf": etf,
            "change_pct": round(daily, 2),
            "ret_1m": round(ret_1m, 2), "ret_3m": round(ret_3m, 2),
            "rs": round(rs_1m, 2), "trend": trend,
            "momentum": int(momentum), "score": score,
        })

    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows


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
        spx = yf.Ticker("^GSPC").history(period="1y", auto_adjust=True)["Close"].dropna()
        if len(spx) >= 200:
            if spx.iloc[-1] > spx.rolling(200).mean().iloc[-1]:
                score += 40
            if spx.iloc[-1] > spx.rolling(50).mean().iloc[-1]:
                score += 30
    except Exception:
        pass
    try:
        vix = float(yf.Ticker("^VIX").history(period="5d", auto_adjust=True)["Close"].dropna().iloc[-1])
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
