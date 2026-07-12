# -*- coding: utf-8 -*-
"""Technical-analysis toolkit for the Company Deep Dive (Phase 18).

Pure functions over a price DataFrame / Series — MACD, ATR, moving averages,
golden/death-cross detection, support & resistance from REAL swing pivots,
returns over standard windows, volume analysis, and momentum/trend
classification + technical sub-scores. No network here (so it is unit-testable);
the caller passes a real OHLCV frame. Every helper returns None when it cannot
be computed from real data — the UI then shows "אין נתון זמין".

Kept separate from the unit-tested `indicators/technical.py` so existing scoring
logic is untouched (Phase 18 adds, it does not change).
"""
import numpy as np
import pandas as pd

from indicators.technical import rsi


def _last(series):
    s = series.dropna() if series is not None else None
    if s is None or len(s) == 0:
        return None
    v = float(s.iloc[-1])
    return v if v == v else None


def sma(close, n):
    return close.rolling(n).mean()


def ema(close, span):
    return close.ewm(span=span, adjust=False).mean()


def moving_averages(close) -> dict:
    """MA20/50/100/200 (last values) + whether price is above each."""
    price = _last(close)
    out = {"price": round(price, 2) if price is not None else None}
    for n in (20, 50, 100, 200):
        v = _last(sma(close, n)) if len(close.dropna()) >= n else None
        out[f"ma{n}"] = round(v, 2) if v is not None else None
        out[f"above_ma{n}"] = (price > v) if (price is not None and v is not None) else None
    return out


def cross_signal(close, fast=50, slow=200, lookback=10) -> str | None:
    """Detect a recent golden/death cross of the fast vs slow MA.

    Golden = fast crossed ABOVE slow within `lookback` sessions; Death = below.
    Returns 'golden' / 'death' / 'none', or None if not enough history.
    """
    c = close.dropna()
    if len(c) < slow + lookback + 2:
        return None
    f, s = sma(c, fast), sma(c, slow)
    diff = (f - s).dropna()
    if len(diff) < lookback + 2:
        return None
    recent = diff.iloc[-(lookback + 1):]
    signs = np.sign(recent.values)
    for i in range(1, len(signs)):
        if signs[i - 1] <= 0 < signs[i]:
            return "golden"
        if signs[i - 1] >= 0 > signs[i]:
            return "death"
    return "none"


def macd(close, fast=12, slow=26, signal=9) -> dict:
    """MACD line / signal / histogram (last values + direction)."""
    c = close.dropna()
    if len(c) < slow + signal:
        return {"macd": None, "signal": None, "hist": None, "rising": None}
    line = ema(c, fast) - ema(c, slow)
    sig = ema(line, signal)
    hist = line - sig
    h_last, h_prev = _last(hist), (float(hist.iloc[-2]) if len(hist) >= 2 else None)
    return {
        "macd": round(_last(line), 3) if _last(line) is not None else None,
        "signal": round(_last(sig), 3) if _last(sig) is not None else None,
        "hist": round(h_last, 3) if h_last is not None else None,
        "rising": (h_prev is not None and h_last is not None and h_last > h_prev),
        "_series": {"macd": line, "signal": sig, "hist": hist},
    }


def atr(df, n=14) -> float | None:
    """Average True Range (last value) from High/Low/Close."""
    if df is None or not {"High", "Low", "Close"}.issubset(df.columns):
        return None
    h, l, c = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([(h - l).abs(), (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    v = _last(tr.rolling(n).mean())
    return round(v, 2) if v is not None else None


def returns(close) -> dict:
    """Trailing returns over standard windows (%) from a dated Close series."""
    c = close.dropna()
    out = {}
    spans = {"1w": 5, "1m": 21, "3m": 63, "6m": 126, "1y": 252, "3y": 756}
    last = _last(c)
    for k, days in spans.items():
        out[k] = round((last / float(c.iloc[-1 - days]) - 1) * 100, 2) if (last is not None and len(c) > days) else None
    # YTD — needs a DatetimeIndex
    out["ytd"] = None
    try:
        if isinstance(c.index, pd.DatetimeIndex) and len(c):
            yr = c.index[-1].year
            ytd = c[c.index >= pd.Timestamp(year=yr, month=1, day=1)]
            if len(ytd) >= 2:
                out["ytd"] = round((float(ytd.iloc[-1]) / float(ytd.iloc[0]) - 1) * 100, 2)
    except Exception:
        pass
    return out


def high_low_52w(close) -> dict:
    c = close.dropna().tail(252)
    if len(c) < 2:
        return {"high": None, "low": None, "dist_from_high": None}
    price, hi, lo = float(c.iloc[-1]), float(c.max()), float(c.min())
    return {"high": round(hi, 2), "low": round(lo, 2),
            "dist_from_high": round((hi - price) / hi * 100, 2) if hi > 0 else None}


def volume_analysis(df) -> dict:
    """Current vs average volume, ratio, spike, and OBV-slope accumulation flag."""
    if df is None or "Volume" not in df.columns:
        return {"current": None, "avg20": None, "ratio": None, "spike": None, "flow": None}
    vol = df["Volume"].dropna()
    cur = _last(vol)
    avg = _last(vol.rolling(20).mean())
    ratio = round(cur / avg, 2) if (cur and avg) else None
    # OBV slope over last 20 sessions -> accumulation / distribution
    flow = None
    try:
        c = df["Close"].dropna()
        obv = (np.sign(c.diff().fillna(0)) * df["Volume"].reindex(c.index).fillna(0)).cumsum()
        tail = obv.tail(20)
        if len(tail) >= 5:
            slope = np.polyfit(range(len(tail)), tail.values, 1)[0]
            flow = "צבירה (Accumulation)" if slope > 0 else "פיזור (Distribution)"
    except Exception:
        pass
    return {"current": int(cur) if cur else None, "avg20": int(avg) if avg else None,
            "ratio": ratio, "spike": (ratio is not None and ratio >= 1.5), "flow": flow}


def _pivots(df, window=5, lookback=160):
    """Swing pivots from REAL highs/lows: ([(high, vol_ok)], [(low, vol_ok)], price).

    vol_ok = the pivot day's volume was above its 20-day average (volume-confirmed
    levels are preferred when choosing support/resistance). Returns (None, None,
    None) when there isn't enough history — never invents levels.
    """
    if df is None or "Close" not in getattr(df, "columns", []):
        return None, None, None
    c = df["Close"].dropna().tail(lookback)
    if len(c) < window * 2 + 1:
        return None, None, None
    hi = df["High"].reindex(c.index).fillna(c) if "High" in df.columns else c
    lo = df["Low"].reindex(c.index).fillna(c) if "Low" in df.columns else c
    vol = df["Volume"].reindex(c.index) if "Volume" in df.columns else None
    vavg = vol.rolling(20).mean() if vol is not None else None
    price = float(c.iloc[-1])
    piv_hi, piv_lo = [], []
    for i in range(window, len(c) - window):
        wh, wl = hi.iloc[i - window:i + window + 1], lo.iloc[i - window:i + window + 1]
        vok = bool(vol is not None and vavg is not None and vavg.iloc[i] == vavg.iloc[i]
                   and vavg.iloc[i] > 0 and vol.iloc[i] > vavg.iloc[i])
        if hi.iloc[i] == wh.max():
            piv_hi.append((float(hi.iloc[i]), vok))
        if lo.iloc[i] == wl.min():
            piv_lo.append((float(lo.iloc[i]), vok))
    return piv_hi, piv_lo, price


def support_resistance(df, window=5, lookback=160) -> dict:
    """Nearest support/resistance from REAL swing pivots (no invented levels)."""
    piv_hi, piv_lo, price = _pivots(df, window, lookback)
    if price is None:
        return {"support": None, "resistance": None}
    res = [p for p, _ in piv_hi if p > price]
    sup = [p for p, _ in piv_lo if p < price]
    return {"support": round(max(sup), 2) if sup else None,
            "resistance": round(min(res), 2) if res else None}


NO_LEVEL = "אין רמת תמיכה/התנגדות אמינה"


def sr_levels(df, window=5, lookback=130) -> dict | None:
    """Full support/resistance analysis (Phase 24) from REAL price history only.

    Methodology (see SUPPORT_RESISTANCE.md): swing pivots over ~6 months
    (volume-confirmed pivots preferred) + the 52-week high/low as candidate
    levels; MA20/50/100/200 within 2% of price are flagged as DYNAMIC levels.
    Support is always BELOW price, resistance always ABOVE. If price trades
    above all recent pivot highs → 'breakout' status; below all pivot lows →
    'breakdown'. Levels are technical ESTIMATES, not guaranteed floors/ceilings.
    """
    piv_hi, piv_lo, price = _pivots(df, window, lookback)
    if price is None:
        return None
    c = df["Close"].dropna()
    hl = high_low_52w(c)

    # A level must clear the price by ≥0.1% — otherwise rounding can turn the
    # current bar itself (e.g. today's 52w high) into a fake level at ~price.
    lo_cut, hi_cut = price * 0.999, price * 1.001

    def _nearest(cands, below):
        pool = [(p, v) for p, v in cands if (p < lo_cut if below else p > hi_cut)]
        if not pool:
            return None
        pref = [p for p, v in pool if v] or [p for p, _ in pool]
        return max(pref) if below else min(pref)

    sup_cands = list(piv_lo) + ([(hl["low"], False)] if hl.get("low") and hl["low"] < lo_cut else [])
    res_cands = list(piv_hi) + ([(hl["high"], False)] if hl.get("high") and hl["high"] > hi_cut else [])
    support = _nearest(sup_cands, below=True)
    resistance = _nearest(res_cands, below=False)

    dist_sup = round((support / price - 1) * 100, 1) if support else None      # negative
    dist_res = round((resistance / price - 1) * 100, 1) if resistance else None  # positive

    # Dynamic MA levels within 2% of price.
    ma = moving_averages(c)
    dyn = []
    for n in (20, 50, 100, 200):
        v = ma.get(f"ma{n}")
        if v and abs(v - price) / price <= 0.02:
            dyn.append({"name": f"MA{n}", "price": round(v, 2),
                        "side": "תמיכה דינמית" if v <= price else "התנגדות דינמית"})

    # Status: price above EVERY observed level (incl. 52w high) → breakout;
    # below every observed level → breakdown.
    status = "normal"
    if resistance is None and support is not None:
        status = "breakout"
    elif support is None and resistance is not None:
        status = "breakdown"

    rr = rr_label = None
    if dist_res is not None and dist_sup not in (None, 0) and abs(dist_sup) > 0.05:
        rr = round(dist_res / abs(dist_sup), 2)
        rr_label = "אטרקטיבי" if rr > 2.0 else ("מאוזן" if rr >= 1.0 else "לא אטרקטיבי")

    if status == "breakout":
        interp = "המניה נסחרת מעל כל שיאי התנודה האחרונים — פריצה מעל התנגדות."
    elif status == "breakdown":
        interp = "המניה נסחרת מתחת לכל שפלי התנודה האחרונים — שבירה מתחת לתמיכה."
    elif dist_res is not None and dist_sup is not None:
        closer_res = dist_res < abs(dist_sup)
        interp = ("המניה קרובה יותר להתנגדות מאשר לתמיכה — יחס סיכון/סיכוי פחות אטרקטיבי."
                  if closer_res else
                  "המניה קרובה יותר לתמיכה מאשר להתנגדות — יחס סיכון/סיכוי נוח יותר.")
    else:
        interp = NO_LEVEL

    return {
        "price": round(price, 2),
        "support": round(support, 2) if support else None,
        "resistance": round(resistance, 2) if resistance else None,
        "dist_support_pct": dist_sup, "dist_resistance_pct": dist_res,
        "breakout_level": round(resistance, 2) if resistance else None,
        "breakdown_level": round(support, 2) if support else None,
        "dynamic_ma": dyn, "high_52w": hl.get("high"), "low_52w": hl.get("low"),
        "risk_reward": rr, "risk_reward_label": rr_label,
        "status": status, "interpretation": interp,
    }


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


PERIOD_DAYS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252, "3Y": 756, "5Y": 1260}


def performance(close, mkt_close=None, period="1Y", start=None, end=None) -> dict | None:
    """Presentation-support performance metrics over a window (NOT scoring).

    Returns stock return %, benchmark (S&P) return %, alpha, CAGR, annualized
    volatility, max drawdown and a simple Sharpe — all computed from the already
    fetched price history. None fields where not computable.
    """
    c = close.dropna()
    if len(c) < 2:
        return None

    def _anchor(ts):
        """Match a boundary timestamp to the index timezone (live yfinance data
        is tz-aware; a naive Timestamp raises on comparison)."""
        ts = pd.Timestamp(ts)
        tz = getattr(c.index, "tz", None)
        if tz is not None:
            ts = ts.tz_localize(tz) if ts.tzinfo is None else ts.tz_convert(tz)
        return ts

    if period == "CUSTOM" and start is not None and end is not None:
        win = c[(c.index >= _anchor(start)) & (c.index <= _anchor(end))]
    elif period == "YTD":
        win = c[c.index >= _anchor(pd.Timestamp(year=c.index[-1].year, month=1, day=1))] \
            if isinstance(c.index, pd.DatetimeIndex) else c.tail(1)
    elif period == "MAX":
        win = c
    else:
        win = c.tail(PERIOD_DAYS.get(period, 252) + 1)
    if len(win) < 2 or float(win.iloc[0]) <= 0:
        return None
    rets = win.pct_change().dropna()
    n = len(win)
    stock = (float(win.iloc[-1]) / float(win.iloc[0]) - 1) * 100
    cagr = ((float(win.iloc[-1]) / float(win.iloc[0])) ** (252.0 / n) - 1) * 100 if n > 5 else None
    vol = float(rets.std() * np.sqrt(252) * 100) if len(rets) >= 5 else None
    maxdd = float((win / win.cummax() - 1.0).min() * 100)
    sharpe = (float(rets.mean() / rets.std()) * np.sqrt(252)) if len(rets) >= 5 and rets.std() > 0 else None
    bench = alpha = None
    if mkt_close is not None:
        m = mkt_close.dropna()
        mw = m[(m.index >= win.index[0]) & (m.index <= win.index[-1])]
        if len(mw) >= 2 and float(mw.iloc[0]) > 0:
            bench = (float(mw.iloc[-1]) / float(mw.iloc[0]) - 1) * 100
            alpha = stock - bench
    return {"period": period, "start": win.index[0], "end": win.index[-1], "n": n,
            "stock": round(stock, 2), "bench": round(bench, 2) if bench is not None else None,
            "alpha": round(alpha, 2) if alpha is not None else None,
            "cagr": round(cagr, 2) if cagr is not None else None,
            "vol": round(vol, 1) if vol is not None else None,
            "maxdd": round(maxdd, 1),
            "sharpe": round(sharpe, 2) if sharpe is not None else None}


def trend_class(price, ma50, ma200, ret_3m) -> str:
    """Classify the trend into 5 buckets from price vs MAs + 3-month return."""
    if None in (price, ma50, ma200):
        return "לא ידוע"
    r = ret_3m if ret_3m is not None else 0
    if price > ma50 > ma200 and r >= 15:
        return "מגמת עלייה חזקה"
    if price > ma50 and price > ma200:
        return "מגמת עלייה"
    if price < ma50 < ma200 and r <= -15:
        return "מגמת ירידה חזקה"
    if price < ma50 and price < ma200:
        return "מגמת ירידה"
    return "דשדוש (Sideways)"


def momentum_class(rsi14, macd_hist, ret_1m) -> str:
    r1 = ret_1m if ret_1m is not None else 0
    h = macd_hist if macd_hist is not None else 0
    if rsi14 is None:
        return "לא ידוע"
    if rsi14 >= 55 and h > 0 and r1 > 0:
        return "חזק"
    if rsi14 < 45 and h < 0:
        return "חלש"
    return "ניטרלי"


def sub_scores(m: dict, vol_annual, ret_3m) -> dict:
    """0-100 technical sub-scores: trend / momentum / volume / volatility."""
    price = m.get("Price")
    # Trend: MAs below price + 3m return
    above = sum(1 for k in ("MA20", "MA50", "MA200") if m.get(k) and price and price > m[k])
    trend = _clamp(above / 3 * 70 + _clamp(((ret_3m or 0) + 10) / 35 * 30, 0, 30))
    # Momentum: RSI band + proximity
    rsi14 = m.get("RSI14") or 50
    mom = _clamp((20 if 50 <= rsi14 <= 75 else 10 if 40 <= rsi14 < 50 else 8 if 75 < rsi14 <= 80 else 0) * 2
                 + _clamp((100 - (m.get("DistFromHigh%") or 0) * 4)) * 0.6)
    # Volume: ratio 1.0->0, 1.5+ ->100
    vr = m.get("VolRatio") or 0
    volsc = _clamp((vr - 1.0) / 0.5 * 100) if vr >= 1 else 0
    # Volatility (calmer = higher): 15% -> ~100, 60% -> ~0
    volat = _clamp(100 - ((vol_annual - 15) / 45 * 100)) if vol_annual is not None else None
    return {"trend": int(round(trend)), "momentum": int(round(mom)),
            "volume": int(round(volsc)), "volatility": int(round(volat)) if volat is not None else None}
