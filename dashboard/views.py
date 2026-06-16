# -*- coding: utf-8 -*-
"""Presentation-only data shaping for the Opportunities / Sector screens.

Pure functions over the precomputed `universe.json` + `market_overview.json`
artifacts (NO scoring changes, NO live calls). Company names resolve from the
enriched artifact → read-only names cache → ticker. Shared by desktop (app.py)
and mobile (mobile.py) so both stay consistent. Unit-tested.
"""
import json
import os

import config
from market import SECTOR_EN_TO_HE

RISK_ORD = {"נמוך": 1, "בינוני": 2, "גבוה": 3, "גבוה מאוד": 4}
RISK_REV = {1: "נמוך", 2: "בינוני", 3: "גבוה", 4: "גבוה מאוד"}


def names_cache() -> dict:
    """Read-only company-name cache ({ticker: name}); {} if absent."""
    try:
        with open(os.path.join(config.DATA_DIR, "names_cache.json"), encoding="utf-8") as fh:
            c = json.load(fh)
            return c if isinstance(c, dict) else {}
    except Exception:
        return {}


def build_lookup(uni: dict) -> dict:
    """Merge per-ticker rows: whole-universe `all` overlaid with enriched `opportunities`."""
    lk = {}
    for r in uni.get("all", []):
        if r.get("Ticker"):
            lk[r["Ticker"]] = dict(r)
    for r in uni.get("opportunities", []):
        if r.get("Ticker"):
            lk.setdefault(r["Ticker"], {}).update(r)
    return lk


def name_for(ticker, lookup, nc):
    """Company name with fallback chain → never blank ('Unknown Company')."""
    r = lookup.get(ticker, {})
    return r.get("Name") or nc.get(ticker) or "Unknown Company"


company_name = name_for   # alias: company name with fallback → 'Unknown Company'


# Bilingual risk badge: level → (emoji, Hebrew, English, color)
RISK_BADGE = {
    "נמוך": ("🟢", "סיכון נמוך", "Low Risk", "#22c55e"),
    "בינוני": ("🟡", "סיכון בינוני", "Medium Risk", "#facc15"),
    "גבוה": ("🟠", "סיכון גבוה", "High Risk", "#fb923c"),
    "גבוה מאוד": ("🔴", "סיכון גבוה מאוד", "Very High Risk", "#ef4444"),
}


def risk_badge(level):
    return RISK_BADGE.get(level, ("⚪", level or "—", "", "#94A3B8"))


def score_band_color(v):
    """Score V2 badge color: 80+ green · 70+ green-blue · 60+ yellow · 50+ orange · else red."""
    if not isinstance(v, (int, float)) or v != v:
        return "#94A3B8"
    return ("#22c55e" if v >= 80 else "#38bdf8" if v >= 70 else "#facc15"
            if v >= 60 else "#fb923c" if v >= 50 else "#ef4444")


def momentum_emoji(m):
    if not isinstance(m, (int, float)) or m != m:
        return "➡️"
    return "🚀" if m >= 50 else "📈" if m >= 15 else "➡️" if m > -5 else "📉"


def kpi_highlights(uni, mkt):
    """Top-summary-bar picks: strongest sector, best momentum, highest score, most undervalued."""
    secs = sector_intel(uni, mkt)
    strongest = (max(secs, key=lambda r: r["sector_score"] if isinstance(r["sector_score"], (int, float)) else -1)
                 if secs else None)
    opps = uni.get("opportunities", [])

    def _top(metric):
        cand = [o for o in opps if isinstance(o.get(metric), (int, float))]
        return max(cand, key=lambda o: o[metric]) if cand else None
    return {"strongest": strongest, "best_mom": _top("Ret3m"),
            "high_score": _top("ScoreV2"), "undervalued": _top("Valuation")}


def ranking_rows(uni: dict, key: str, lookup=None, nc=None, n: int = 10) -> list:
    """Top-N rows for a ranking list: ticker, name, sector, score_v2, risk."""
    lookup = build_lookup(uni) if lookup is None else lookup
    nc = names_cache() if nc is None else nc
    out = []
    for t in (uni.get("rankings", {}).get(key) or [])[:n]:
        r = lookup.get(t, {})
        out.append({"ticker": t, "name": name_for(t, lookup, nc),
                    "sector": r.get("Sector"), "score_v2": r.get("ScoreV2"),
                    "risk": r.get("RiskLevel")})
    return out


def sector_intel(uni: dict, mkt: dict) -> list:
    """Per-sector intelligence rows from enriched opportunities + market sectors.

    rank · sector · n_opportunities · top company · avg ScoreV2 · avg risk ·
    momentum · relative strength · recommendation (Overweight/Neutral/Underweight).
    """
    by = {}
    for r in uni.get("opportunities", []):
        s = r.get("Sector")
        if s:
            by.setdefault(s, []).append(r)
    msec = {s.get("sector"): s for s in (mkt.get("sectors") or [])}
    rows = []
    for sec_en, items in by.items():
        scores = [x.get("ScoreV2") for x in items if isinstance(x.get("ScoreV2"), (int, float))]
        avg_score = round(sum(scores) / len(scores)) if scores else None
        vals = [x.get("Valuation") for x in items if isinstance(x.get("Valuation"), (int, float))]
        avg_val = round(sum(vals) / len(vals)) if vals else None
        top = max(items, key=lambda x: x.get("ScoreV2") or 0)
        risks = [RISK_ORD[x["RiskLevel"]] for x in items if x.get("RiskLevel") in RISK_ORD]
        avg_risk = RISK_REV.get(round(sum(risks) / len(risks))) if risks else None
        he = SECTOR_EN_TO_HE.get(sec_en, sec_en)
        si = msec.get(he, {})
        ss = si.get("score")
        reco = ("Overweight" if isinstance(ss, (int, float)) and ss >= 66
                else "Underweight" if isinstance(ss, (int, float)) and ss < 40 else "Neutral")
        rows.append({"sector": sec_en, "sector_he": he, "n": len(items),
                     "top": top.get("Ticker"), "top_name": top.get("Name") or top.get("Ticker"),
                     "avg_score": avg_score, "avg_val": avg_val, "avg_risk": avg_risk,
                     "sector_score": ss, "momentum": si.get("momentum"),
                     "ret_3m": si.get("ret_3m"), "rs": si.get("rs"), "reco": reco})
    rows.sort(key=lambda x: -(x["sector_score"] if isinstance(x["sector_score"], (int, float)) else -1))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def sector_summary(rows: list) -> dict:
    """Headline sectors: strongest, weakest, most opportunities, best average score."""
    if not rows:
        return {}
    ws = [r for r in rows if isinstance(r["sector_score"], (int, float))]
    wa = [r for r in rows if isinstance(r["avg_score"], (int, float))]
    return {
        "strongest": max(ws, key=lambda r: r["sector_score"]) if ws else None,
        "weakest": min(ws, key=lambda r: r["sector_score"]) if ws else None,
        "most": max(rows, key=lambda r: r["n"]),
        "best_avg": max(wa, key=lambda r: r["avg_score"]) if wa else None,
    }
