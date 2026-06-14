# -*- coding: utf-8 -*-
"""Risk Intelligence Engine (Phase 14, Part 2).

Professional risk metrics from real price history — Beta (vs S&P 500),
annualized Volatility, Maximum Drawdown — combined into a 0-100 Risk Score,
a Risk Category, and human-readable Risk Warnings. Also computes portfolio-level
risk: weighted beta/volatility, a holdings correlation matrix, and concentration
(position + sector) risk. Pure functions over pandas Series — unit-tested.
"""
import numpy as np
import pandas as pd


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def _returns(close):
    return close.dropna().pct_change().dropna()


# ---------------------------------------------------------------------------
# Per-stock metrics
# ---------------------------------------------------------------------------

def beta(stock_close, market_close, window: int = 252):
    """Beta vs the market over `window` trading days (None if insufficient)."""
    if stock_close is None or market_close is None:
        return None
    df = pd.concat([_returns(stock_close), _returns(market_close)], axis=1, join="inner").dropna()
    if len(df) < 30:
        return None
    df = df.tail(window)
    var = df.iloc[:, 1].var()
    if not var or var <= 0:
        return None
    return round(float(df.iloc[:, 0].cov(df.iloc[:, 1]) / var), 2)


def volatility(close, window: int = 252):
    """Annualized volatility in %."""
    r = _returns(close).tail(window)
    if len(r) < 20:
        return None
    return round(float(r.std() * np.sqrt(252) * 100), 1)


def max_drawdown(close, window: int = 252):
    """Largest peak-to-trough decline (%, negative) over the window."""
    s = close.dropna().tail(window)
    if len(s) < 20:
        return None
    dd = s / s.cummax() - 1.0
    return round(float(dd.min() * 100), 1)


def risk_score(vol, bta, mdd):
    """0-100 (higher = riskier) from volatility (45%) + beta (25%) + maxDD (30%)."""
    parts, weights = [], []
    if vol is not None:
        parts.append(_clamp((vol - 15) / (60 - 15) * 100)); weights.append(0.45)
    if bta is not None:
        parts.append(_clamp((bta - 0.7) / (1.8 - 0.7) * 100)); weights.append(0.25)
    if mdd is not None:
        parts.append(_clamp((abs(mdd) - 15) / (60 - 15) * 100)); weights.append(0.30)
    if not parts:
        return None
    return int(round(float(np.average(parts, weights=weights))))


def category(score):
    if score is None:
        return "לא ידוע"
    return ("נמוך" if score < 30 else "בינוני" if score < 55
            else "גבוה" if score < 75 else "גבוה מאוד")


def risk_profile(stock_close, market_close) -> dict:
    """Full per-stock risk profile."""
    bta = beta(stock_close, market_close)
    vol = volatility(stock_close)
    mdd = max_drawdown(stock_close)
    rs = risk_score(vol, bta, mdd)
    warnings = []
    if bta is not None and bta > 1.3:
        warnings.append(f"ביתא גבוהה ({bta}) — רגיש לתנודות שוק")
    if vol is not None and vol > 45:
        warnings.append(f"תנודתיות שנתית גבוהה ({vol}%)")
    if mdd is not None and mdd < -35:
        warnings.append(f"ירידה מקסימלית עמוקה ({mdd}%)")
    return {"beta": bta, "volatility": vol, "max_drawdown": mdd,
            "risk_score": rs, "category": category(rs), "warnings": warnings}


# ---------------------------------------------------------------------------
# Portfolio-level risk
# ---------------------------------------------------------------------------

def correlation_pairs(closes_map: dict, threshold: float = 0.7) -> dict:
    """Return {matrix, high_pairs} from holdings' return correlations.

    closes_map: {ticker: Close Series}. `matrix` is {t: {t2: corr}} (rounded).
    `high_pairs` lists pairs with |corr| >= threshold (hidden concentration).
    """
    rets = {t: _returns(s) for t, s in closes_map.items() if s is not None}
    if len(rets) < 2:
        return {"matrix": {}, "high_pairs": []}
    rdf = pd.DataFrame(rets).dropna()
    if len(rdf) < 30:
        return {"matrix": {}, "high_pairs": []}
    corr = rdf.corr().round(2)
    matrix = {t: {t2: float(corr.loc[t, t2]) for t2 in corr.columns} for t in corr.index}
    pairs = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = float(corr.iloc[i, j])
            if abs(c) >= threshold:
                pairs.append({"a": cols[i], "b": cols[j], "corr": c})
    pairs.sort(key=lambda p: -abs(p["corr"]))
    return {"matrix": matrix, "high_pairs": pairs}


def portfolio_risk(positions: list, betas: dict, vols: dict, sector_exposure: dict) -> dict:
    """Weighted beta/volatility + concentration risk + warnings.

    positions: [{ticker, weight, ...}]; betas/vols: {ticker: value}.
    """
    if not positions:
        return {}
    wbeta = wvol = wsum = 0.0
    for p in positions:
        w = p["weight"] / 100
        if betas.get(p["ticker"]) is not None:
            wbeta += w * betas[p["ticker"]]
        if vols.get(p["ticker"]) is not None:
            wvol += w * vols[p["ticker"]]
        wsum += w
    weights = [p["weight"] / 100 for p in positions]
    hhi = sum(w * w for w in weights) or 1
    eff_n = 1 / hhi
    max_pos = max(p["weight"] for p in positions)
    max_sector = max(sector_exposure.values()) if sector_exposure else 0
    # Concentration risk 0-100 (higher = more concentrated)
    conc = _clamp(((max_pos - 20) / 30 * 50) + ((max_sector - 25) / 45 * 50))

    warnings = []
    if max_pos > 25:
        warnings.append(f"פוזיציה בודדת גדולה: {max_pos:.0f}% מהתיק")
    if max_sector > 40:
        warnings.append(f"ריכוז סקטוריאלי גבוה: {max_sector:.0f}%")
    if eff_n < 4:
        warnings.append(f"פיזור נמוך: {eff_n:.1f} פוזיציות אפקטיביות")
    if wbeta > 1.2:
        warnings.append(f"ביתא תיק גבוהה ({wbeta:.2f}) — רגישות גבוהה לשוק")

    return {
        "weighted_beta": round(wbeta, 2),
        "weighted_volatility": round(wvol, 1),
        "effective_positions": round(eff_n, 1),
        "max_position_pct": round(max_pos, 1),
        "max_sector_pct": round(max_sector, 1),
        "concentration_risk": int(round(conc)),
        "warnings": warnings,
    }
