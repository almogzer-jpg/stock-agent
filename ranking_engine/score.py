# -*- coding: utf-8 -*-
"""0-100 quality/momentum scoring engine."""
from config import VOLUME_SPIKE, RSI_MIN, RSI_MAX


def score_stock(m: dict) -> int:
    """Compute a 0-100 score from a metrics dict.

    Weighted blend of the breakout ingredients plus longer-term trend health,
    so strong-trend names still rank even without a fresh volume spike.

    Weights (sum to 100):
        25  trend structure  (price vs 50/200-day MAs, 50>200 alignment)
        20  proximity to 52-week high
        20  RSI momentum band
        20  volume confirmation
        15  short-term posture (price vs 20-day MA)
    """
    score = 0.0

    # --- Trend structure (25 pts) ---
    if m["Price"] > m["MA50"]:
        score += 8
    if m["Price"] > m["MA200"]:
        score += 9
    if m["MA50"] > m["MA200"]:          # "golden" alignment of the averages
        score += 8

    # --- Proximity to 52-week high (20 pts) ---
    # 0% away -> full 20; 20%+ away -> 0 (linear in between).
    dist = m["DistFromHigh%"]
    score += max(0.0, 20.0 * (1.0 - dist / 20.0))

    # --- RSI momentum (20 pts) ---
    rsi = m["RSI14"]
    if RSI_MIN <= rsi <= RSI_MAX:
        score += 20                      # squarely in the healthy band
    elif 40 <= rsi < RSI_MIN:
        score += 10                      # building momentum
    elif RSI_MAX < rsi <= 80:
        score += 8                       # strong but getting overbought
    # weak (<40) or extreme (>80): 0 pts

    # --- Volume confirmation (20 pts) ---
    vr = m["VolRatio"]
    if vr >= VOLUME_SPIKE:
        score += 20                      # clear volume spike
    elif vr >= 1.0:
        score += 20.0 * (vr - 1.0) / (VOLUME_SPIKE - 1.0)  # 1.0x->0, 1.5x->20
    # below-average volume: 0 pts

    # --- Short-term posture (15 pts) ---
    if m["Price"] > m["MA20"]:
        score += 15

    return int(round(max(0.0, min(100.0, score))))
