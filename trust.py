# -*- coding: utf-8 -*-
"""Trust & Validation engine (Phase 14, Part 6).

Answers "how much should I trust this recommendation?" with a 0-100 Trust Score
built from seven real factors, a confidence category, and explicit
strengths/limitations (why trust / why be cautious). Pure functions over a
stock row + its backtest stats. No placeholders.
"""

FUND_FIELDS = ["RevenueGrowth", "EPSGrowth", "FCFGrowth", "OperatingMargin",
               "DebtToEquity", "ROIC", "PEG", "ForwardPE"]

# Trust factor weights (sum to 100).
WEIGHTS = {"data_quality": 15, "historical_validation": 20, "sample_size": 15,
           "out_of_sample": 15, "fundamental_completeness": 10,
           "score_consistency": 15, "risk_model": 10}


def _num(v):
    return v if isinstance(v, (int, float)) and v == v else None


def _band(x, lo, hi):
    if x is None or hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def _category(score):
    return "גבוה" if score >= 66 else "בינוני" if score >= 40 else "נמוך"


def trust_score(row, backtest: dict | None = None) -> dict:
    """0-100 Trust Score + category + per-factor points + strengths/limitations."""
    bt = backtest or {}
    occ = bt.get("occurrences") or 0
    wr, oos = bt.get("win_rate"), bt.get("oos_win_rate")

    fund_present = sum(1 for f in FUND_FIELDS if _num(row.get(f)) is not None)
    fund_compl = fund_present / len(FUND_FIELDS)
    comp_compl = (_num(row.get("Completeness")) or 0) / 100

    subs = [s for s in (_num(row.get("Score")), _num(row.get("ScoreFundamental")),
                        _num(row.get("ScoreSentiment"))) if s is not None]
    consistency = (1 - min(1.0, (max(subs) - min(subs)) / 100)) if len(subs) >= 2 else 0.5
    risk_present = all(_num(row.get(k)) is not None for k in ("Beta", "Volatility", "MaxDrawdown"))

    sub = {
        "data_quality": 0.5 + 0.5 * (1 if _num(row.get("ScoreFundamental")) is not None else 0),
        "historical_validation": _band(wr, 40, 70) if (wr is not None and occ >= 4) else 0.2,
        "sample_size": _band(occ, 2, 10),
        "out_of_sample": _band(oos, 40, 70) if oos is not None else 0.3,
        "fundamental_completeness": fund_compl,
        "score_consistency": 0.5 * comp_compl + 0.5 * consistency,
        "risk_model": 1.0 if risk_present else 0.3,
    }
    factors = {k: round(WEIGHTS[k] * v, 1) for k, v in sub.items()}
    score = int(round(min(100.0, max(0.0, sum(factors.values())))))

    strengths, limitations = [], []
    if occ >= 8 and wr is not None and wr >= 55:
        strengths.append(f"אומת היסטורית: {wr:.0f}% הצלחה על {occ} מופעים")
    elif 0 < occ < 4:
        limitations.append(f"מדגם היסטורי קטן ({occ} מופעים)")
    elif occ == 0:
        limitations.append("אין מספיק איתותים היסטוריים לאימות")
    if oos is not None and oos >= 50:
        strengths.append(f"ביצועי Out-of-Sample עקביים ({oos:.0f}%)")
    elif oos is not None and oos < 40:
        limitations.append(f"ביצועי Out-of-Sample חלשים ({oos:.0f}%)")
    elif oos is None:
        limitations.append("ללא אימות Out-of-Sample")
    if fund_compl >= 0.8:
        strengths.append("נתונים פונדמנטליים מלאים")
    elif fund_compl < 0.5:
        limitations.append("נתונים פונדמנטליים חלקיים")
    if consistency >= 0.7:
        strengths.append("אותות מסכימים זה עם זה")
    elif consistency < 0.4:
        limitations.append("אותות סותרים (טכני מול פונדמנטלי)")
    if risk_present:
        strengths.append("מודל סיכון מלא (ביתא/תנודתיות/Drawdown)")
    if not strengths:
        strengths.append("אין חוזקות בולטות")
    if not limitations:
        limitations.append("אין מגבלות חריגות")

    return {"score": score, "category": _category(score), "factors": factors,
            "strengths": strengths, "limitations": limitations}


def signal_reliability(row, backtest: dict | None = None) -> dict:
    """Reliability metrics for one recommendation (pulls from row + backtest)."""
    bt = backtest or {}
    conf = _num(row.get("Confidence")) or 0
    return {
        "confidence": int(conf),
        "category": _category(conf),
        "hist_win_rate": bt.get("win_rate"),
        "occurrences": bt.get("occurrences"),
        "avg_return": bt.get("avg_return"),
        "excess_return": bt.get("benchmark_rel"),     # vs S&P 500
        "max_drawdown": bt.get("max_drawdown"),
    }
