# -*- coding: utf-8 -*-
"""Proprietary calculated indicators — derived from REAL data, never faked.

These metrics have no exact free source, so we compute transparent estimates
from real market data and label them clearly as "מדד קנייני (מחושב)" in the UI.
Every function returns its value PLUS a Hebrew `method` string explaining how
it was calculated, so nothing is a black box.

Inputs are the scan DataFrame (per-stock real metrics) and real market data
(VIX, sector ETF moves). No extra network calls here — pure computation.
"""
import numpy as np


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


# ---------------------------------------------------------------------------
# Market breadth — how broad the strength is across the watchlist
# ---------------------------------------------------------------------------

def market_breadth(df) -> dict:
    """Breadth from the scanned universe (all real per-stock data)."""
    n = len(df)
    if n == 0:
        return {"score": None, "method": "אין נתונים."}
    above50 = float((df["Price"] > df["MA50"]).mean() * 100)
    above200 = float((df["Price"] > df["MA200"]).mean() * 100)
    adv = int((df["DailyChange%"] > 0).sum())
    dec = int((df["DailyChange%"] < 0).sum())
    ad_ratio = adv / dec if dec else float(adv)
    # Breadth score: average of the three "participation" gauges.
    score = round((above50 + above200 + (adv / n * 100)) / 3, 1)
    return {
        "score": score,
        "above50": round(above50, 1),
        "above200": round(above200, 1),
        "advancers": adv,
        "decliners": dec,
        "ad_ratio": round(ad_ratio, 2),
        "method": (f"ממוצע של: {above50:.0f}% מהמניות מעל ממוצע 50, "
                   f"{above200:.0f}% מעל ממוצע 200, ו‑{adv}/{n} עולות היום."),
    }


# ---------------------------------------------------------------------------
# Fear & Greed — proprietary, from VIX + breadth + momentum
# ---------------------------------------------------------------------------

def fear_greed(df, vix, breadth: dict | None = None) -> dict:
    """0-100 (0 = פחד קיצוני, 100 = חמדנות קיצונית). Proprietary."""
    breadth = breadth or market_breadth(df)
    parts, weights = [], []

    # VIX component: VIX 12 -> greedy(100), VIX 35 -> fearful(0).
    if vix is not None:
        vix_comp = _clamp((35.0 - float(vix)) / (35.0 - 12.0) * 100.0)
        parts.append(vix_comp); weights.append(0.35)

    # Breadth component (already 0-100).
    if breadth.get("score") is not None:
        parts.append(breadth["score"]); weights.append(0.30)

    # Momentum component: average RSI mapped around 50.
    if "RSI14" in df and len(df):
        rsi_comp = _clamp((float(df["RSI14"].mean()) - 30) / (70 - 30) * 100)
        parts.append(rsi_comp); weights.append(0.20)

    # Advance/decline tilt today.
    adv, dec = breadth.get("advancers", 0), breadth.get("decliners", 0)
    if (adv + dec) > 0:
        parts.append(adv / (adv + dec) * 100); weights.append(0.15)

    if not parts:
        return {"score": None, "label": "אין נתון", "method": "חסרים נתונים."}
    score = round(float(np.average(parts, weights=weights)), 0)
    if score >= 75:   label = "חמדנות קיצונית"
    elif score >= 55: label = "חמדנות"
    elif score >= 45: label = "ניטרלי"
    elif score >= 25: label = "פחד"
    else:             label = "פחד קיצוני"
    return {
        "score": int(score), "label": label,
        "method": "שקלול VIX (35%), רוחב שוק (30%), מומנטום RSI (20%), "
                  "ויחס עולות/יורדות (15%) — כולם מנתונים אמיתיים.",
    }


# ---------------------------------------------------------------------------
# Capital flow — proprietary, from sector ETF relative strength
# ---------------------------------------------------------------------------

def capital_flow(sectors: list) -> dict:
    """Estimate sector inflows/outflows from real sector-ETF strength.

    Ranks by Sector Score when available (trend + momentum + relative strength),
    else by daily move. Positive strength = estimated capital inflow.
    """
    if not sectors:
        return {"inflows": [], "outflows": [], "method": "אין נתוני סקטורים."}
    key = "score" if "score" in sectors[0] else "change_pct"
    ranked = sorted(sectors, key=lambda s: s.get(key, 0), reverse=True)
    return {
        "inflows": ranked[:5],
        "outflows": ranked[-5:][::-1],
        "method": "אומדן לפי חוזק סקטוריאלי (מגמה + מומנטום + חוזק יחסי מול S&P) "
                  "מתוך ETF מייצגים. חוזק חיובי = כניסת הון משוערת.",
    }


# ---------------------------------------------------------------------------
# Expected upside — proprietary internal model (per stock)
# ---------------------------------------------------------------------------

def expected_upside(row) -> dict:
    """Heuristic % upside estimate. Proprietary — not a forecast guarantee."""
    dist = float(row.get("DistFromHigh%", 0))      # room back to 52w high
    score = float(row.get("Score", 0))
    # Base: room to reclaim the 52-week high, weighted by technical strength.
    base = dist * (0.4 + 0.6 * score / 100.0)
    # If already near the high, allow a volatility-based extension.
    risk = float(row.get("ScoreRisk", 30))         # 0-100 (higher = more volatile)
    if dist < 3:
        base = max(base, risk / 100.0 * 12.0)      # up to ~12% for high-vol names
    pct = round(_clamp(base, 0, 60), 1)
    return {
        "pct": pct,
        "method": "מודל פנימי: מרחק משיא 52 שבועות משוקלל בציון הטכני, "
                  "ובתוספת תנודתיות לנכסים שכבר בשיא. אומדן, לא הבטחה.",
    }


# ---------------------------------------------------------------------------
# Confidence — proprietary, from signal agreement + data quality + backtest
# ---------------------------------------------------------------------------

def confidence(row, backtest_hit: float | None = None) -> dict:
    """0-100 confidence in the signal. Proprietary."""
    factors = []
    pts = 0.0

    # Number of bullish technical factors (max 5).
    bull = 0
    if row.get("Price", 0) > row.get("MA50", 0):  bull += 1
    if row.get("Price", 0) > row.get("MA200", 0): bull += 1
    if 50 <= row.get("RSI14", 0) <= 75:           bull += 1
    if row.get("VolRatio", 0) >= 1.2:             bull += 1
    if row.get("DistFromHigh%", 100) <= 10:       bull += 1
    pts += bull / 5 * 40
    factors.append(f"{bull}/5 גורמים חיוביים")

    # Signal agreement between technical & sentiment sub-scores.
    tech = float(row.get("Score", 0)); sent = float(row.get("ScoreSentiment", 50))
    agree = 100 - abs(tech - sent)
    pts += agree / 100 * 25
    factors.append("הסכמת אותות" if agree > 70 else "אותות מעורבים")

    # Data quality: do we have fundamentals?
    has_fund = row.get("ScoreFundamental") not in (None, "") and \
        not (isinstance(row.get("ScoreFundamental"), float) and np.isnan(row.get("ScoreFundamental")))
    pts += 15 if has_fund else 0
    factors.append("נתונים פונדמנטליים זמינים" if has_fund else "ללא פונדמנטלי")

    # Backtest hit-rate for this ticker's setup.
    if backtest_hit is not None:
        pts += float(backtest_hit) / 100 * 20
        factors.append(f"בקטסט {backtest_hit:.0f}% הצלחה")

    score = int(round(_clamp(pts)))
    level = "גבוה" if score >= 66 else ("בינוני" if score >= 40 else "נמוך")
    return {
        "score": score, "level": level, "factors": factors,
        "method": "שקלול: מספר גורמים חיוביים (40%), הסכמת אותות (25%), "
                  "איכות נתונים (15%), ושיעור הצלחה בבקטסט (20%).",
    }
