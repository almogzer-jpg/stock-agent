# -*- coding: utf-8 -*-
"""Lightweight headline sentiment — a basic, transparent keyword model.

This is NOT a deep NLP model; it's an honest, simple lexicon score over the
free Yahoo headlines we already fetch. It returns a 0-100 score (50 = neutral)
plus the counts, so the dashboard can show *why*. No paid APIs.
"""

POSITIVE = {
    "beat", "beats", "surge", "surges", "soar", "soars", "jump", "jumps",
    "rally", "rallies", "record", "high", "growth", "upgrade", "upgraded",
    "outperform", "strong", "gains", "gain", "rise", "rises", "boost",
    "profit", "wins", "win", "bullish", "buy", "raises", "raise", "top",
    "tops", "approval", "approved", "expands", "expansion", "launch",
}
NEGATIVE = {
    "miss", "misses", "plunge", "plunges", "drop", "drops", "fall", "falls",
    "slump", "slumps", "downgrade", "downgraded", "weak", "loss", "losses",
    "cut", "cuts", "warning", "warn", "lawsuit", "probe", "investigation",
    "recall", "decline", "declines", "bearish", "sell", "fears", "fear",
    "slowdown", "concern", "concerns", "layoffs", "fraud", "delay", "delays",
}


def score_headlines(headlines: list[dict]) -> dict:
    """Return {score, pos, neg, n} for a list of {title,...} headlines.

    score is 0-100 (50 = neutral / no news). Computed as the share of positive
    keyword hits out of all sentiment-bearing hits, scaled to 0-100.
    """
    if not headlines:
        return {"score": 50, "pos": 0, "neg": 0, "n": 0}

    pos = neg = 0
    for h in headlines:
        words = str(h.get("title", "")).lower().replace(",", " ").split()
        wset = set(words)
        pos += len(wset & POSITIVE)
        neg += len(wset & NEGATIVE)

    total = pos + neg
    if total == 0:
        score = 50                      # news exists but no clear sentiment
    else:
        score = int(round(100 * pos / total))
    return {"score": score, "pos": pos, "neg": neg, "n": len(headlines)}
