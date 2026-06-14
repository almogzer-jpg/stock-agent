# -*- coding: utf-8 -*-
"""Composite Final Score v2 — institutional multi-factor ranking.

Replaces the momentum-only Final Score with a weighted blend of five real
dimensions. Higher = better. Risk enters as RISK HEALTH (100 − risk), so lower
risk lifts the score.

Target weights (Phase 14):
    Fundamental 35% · Technical 25% · Sector 20% · News 10% · Risk 10%

Missing inputs (e.g. no fundamentals for a bank) are handled by RENORMALISING
the weights over the available dimensions — a stock is never silently penalised
to 0 for missing data; instead its `completeness` drops (surfaced for trust).
Every score is fully decomposable into per-dimension contributions.
"""

WEIGHTS_V2 = {"fundamental": 0.35, "technical": 0.25, "sector": 0.20,
              "news": 0.10, "risk": 0.10}

LABELS_HE = {"fundamental": "פונדמנטלי", "technical": "טכני", "sector": "סקטור",
             "news": "חדשות", "risk": "ניהול סיכון"}


def composite_score(technical=None, fundamental=None, sector=None,
                    news=None, risk=None) -> dict | None:
    """Return the v2 score + full contribution breakdown.

    Args are 0-100 dimension scores (risk: higher = riskier). Returns:
        final          int 0-100 (weighted, renormalised)
        contributions  {dim: weighted points}  (sum == final)
        weights        {dim: effective weight after renormalisation}
        raw            {dim: input 0-100 used (risk shown as risk-health)}
        completeness   share of total weight that had data (0-1)
        missing        list of dimensions with no data
    """
    raw = {
        "fundamental": fundamental,
        "technical": technical,
        "sector": sector,
        "news": news,
        # Risk health: low risk -> high contribution.
        "risk": (None if risk is None else max(0.0, min(100.0, 100.0 - risk))),
    }
    available = {k: v for k, v in raw.items() if isinstance(v, (int, float)) and v == v}
    total_w = sum(WEIGHTS_V2[k] for k in available)
    if not available or total_w == 0:
        return None

    contributions, weights, final = {}, {}, 0.0
    for k, v in available.items():
        w = WEIGHTS_V2[k] / total_w          # renormalised
        weights[k] = round(w, 3)
        contributions[k] = round(v * w, 1)
        final += v * w

    return {
        "final": int(round(max(0.0, min(100.0, final)))),
        "contributions": contributions,
        "weights": weights,
        "raw": {k: round(v, 1) for k, v in available.items()},
        "completeness": round(total_w, 2),
        "missing": [k for k in raw if k not in available],
    }


def explain_composite(c: dict) -> str:
    """One-line Hebrew explanation of why the v2 score is what it is."""
    if not c:
        return "אין מספיק נתונים לחישוב ציון משוקלל."
    parts = sorted(c["contributions"].items(), key=lambda kv: kv[1], reverse=True)
    bits = [f"{LABELS_HE[k]} {pts} נק׳ ({int(c['weights'][k]*100)}%)" for k, pts in parts]
    note = ""
    if c["missing"]:
        note = f" · חסר נתון: {', '.join(LABELS_HE[m] for m in c['missing'])} (המשקלים חולקו מחדש)"
    return f"ציון v2 {c['final']} = " + " + ".join(bits) + note
