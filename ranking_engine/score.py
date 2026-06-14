# -*- coding: utf-8 -*-
"""0-100 quality/momentum scoring engine (with transparent breakdown)."""
from config import VOLUME_SPIKE, RSI_MIN, RSI_MAX

# Component weights (sum to 100) — exposed for the UI's score transparency.
WEIGHTS = {"trend": 25, "proximity": 20, "rsi": 20, "volume": 20, "short_term": 15}

# Hebrew labels for the components (shown in the "how is the score built" panel).
COMPONENT_LABELS_HE = {
    "trend": "מבנה מגמה (מול ממוצעים)",
    "proximity": "קרבה לשיא 52 שבועות",
    "rsi": "מומנטום RSI",
    "volume": "אישור נפח",
    "short_term": "מצב קצר-טווח (מול ממוצע 20)",
}


def _components_raw(m: dict) -> dict:
    """Raw (unrounded) point contributions of each scoring component."""
    # Trend structure (25)
    trend = 0.0
    if m["Price"] > m["MA50"]:
        trend += 8
    if m["Price"] > m["MA200"]:
        trend += 9
    if m["MA50"] > m["MA200"]:           # "golden" alignment
        trend += 8

    # Proximity to 52-week high (20): 0% away -> 20; 20%+ -> 0
    proximity = max(0.0, 20.0 * (1.0 - m["DistFromHigh%"] / 20.0))

    # RSI momentum (20)
    rsi = m["RSI14"]
    if RSI_MIN <= rsi <= RSI_MAX:
        rsi_pts = 20.0
    elif 40 <= rsi < RSI_MIN:
        rsi_pts = 10.0
    elif RSI_MAX < rsi <= 80:
        rsi_pts = 8.0
    else:
        rsi_pts = 0.0

    # Volume confirmation (20): 1.0x->0, 1.5x->20
    vr = m["VolRatio"]
    if vr >= VOLUME_SPIKE:
        vol = 20.0
    elif vr >= 1.0:
        vol = 20.0 * (vr - 1.0) / (VOLUME_SPIKE - 1.0)
    else:
        vol = 0.0

    # Short-term posture (15)
    short = 15.0 if m["Price"] > m["MA20"] else 0.0

    return {"trend": trend, "proximity": proximity, "rsi": rsi_pts,
            "volume": vol, "short_term": short}


def score_breakdown(m: dict) -> dict:
    """Rounded component points for display (transparency)."""
    return {k: round(v, 1) for k, v in _components_raw(m).items()}


def score_stock(m: dict) -> int:
    """Compute the 0-100 final (technical-momentum) score.

    Sums the RAW components (so the result is identical to before this refactor —
    no ranking drift). The Final Score is this technical/momentum blend;
    Fundamental / Sector / News / Risk are independent lenses shown alongside it.
    """
    total = sum(_components_raw(m).values())
    return int(round(max(0.0, min(100.0, total))))
