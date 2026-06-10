# -*- coding: utf-8 -*-
"""Per-stock factor sub-scores (each 0-100) for the detail view & radar chart.

Every score is derived from REAL data the engines already produce — no
placeholders. Where a factor's input is unavailable (e.g. fundamentals turned
off), that score is returned as None and the UI shows it as "אין נתון".

Factors:
    technical    — the existing technical score (trend/RSI/volume/proximity)
    fundamental  — valuation & quality (P/E, margins, growth)   [needs fundamentals]
    news         — headline sentiment (0-100, 50 neutral)        [needs news]
    sentiment    — price-action sentiment (position vs MAs, RSI)
    risk         — 0-100 where HIGHER = riskier (volatility + extremes)
"""
import numpy as np

from ranking_engine.score import score_stock


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _annualized_vol(closes) -> float | None:
    """Annualized volatility (%) from a list of recent closes."""
    arr = np.asarray([c for c in closes if c == c], dtype=float) if closes else None
    if arr is None or len(arr) < 20:
        return None
    rets = np.diff(arr) / arr[:-1]
    return float(np.std(rets) * np.sqrt(252) * 100.0)


def fundamental_score(f) -> float | None:
    """0-100 from valuation/quality fields; None if no fundamentals.

    Accepts a dict or a pandas Series (so it works from both run.py and the
    dashboard). Returns None when the fundamental fields aren't present.
    """
    if f is None:
        return None
    has_any = any(f.get(k) not in (None, "") for k in
                  ("TrailingPE", "ProfitMargin", "RevenueGrowth"))
    if not has_any:
        return None

    s = 50.0
    pe = f.get("TrailingPE")
    if isinstance(pe, (int, float)) and pe > 0:
        if pe <= 15:      s += 18
        elif pe <= 25:    s += 10
        elif pe <= 40:    s += 0
        else:             s -= 12          # expensive
    margin = f.get("ProfitMargin")
    if isinstance(margin, (int, float)):
        if margin >= 0.20:   s += 16
        elif margin >= 0.10: s += 8
        elif margin < 0:     s -= 15       # losing money
    growth = f.get("RevenueGrowth")
    if isinstance(growth, (int, float)):
        if growth >= 0.15:   s += 16
        elif growth >= 0.05: s += 8
        elif growth < 0:     s -= 12       # shrinking
    return round(_clamp(s), 1)


def sentiment_score(m: dict) -> float:
    """0-100 price-action sentiment from position vs MAs and RSI."""
    s = 50.0
    if m["Price"] > m["MA50"]:
        s += 15
    if m["Price"] > m["MA200"]:
        s += 15
    s += (m["RSI14"] - 50) * 0.7          # momentum tilt
    return round(_clamp(s), 1)


def risk_score(m: dict, closes=None) -> tuple[float, str]:
    """Return (risk 0-100, Hebrew level). Higher = riskier."""
    risk = 30.0
    vol = _annualized_vol(closes)
    if vol is not None:
        # 15% vol -> calm, 60%+ -> very volatile.
        risk = _clamp((vol - 15.0) / (60.0 - 15.0) * 100.0)
    if m["RSI14"] >= 75:                 # overbought = pullback risk
        risk += 15
    if m["Price"] < m["MA200"]:          # downtrend = elevated risk
        risk += 15
    if m["DistFromHigh%"] > 25:          # far below highs = damaged
        risk += 10
    risk = round(_clamp(risk), 1)
    level = "נמוך" if risk < 33 else ("בינוני" if risk < 66 else "גבוה")
    return risk, level


def factor_scores(m: dict, closes=None, fundamentals: dict | None = None,
                  news_sent: dict | None = None) -> dict:
    """Bundle all sub-scores into one dict for the UI."""
    risk, risk_level = risk_score(m, closes)
    return {
        "technical": score_stock(m),
        "fundamental": fundamental_score(fundamentals),
        "news": (news_sent or {}).get("score"),
        "sentiment": sentiment_score(m),
        "risk": risk,
        "risk_level": risk_level,
    }
