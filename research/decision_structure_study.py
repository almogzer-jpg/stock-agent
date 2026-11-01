# -*- coding: utf-8 -*-
"""Shadow study: what would change if the decision were built from five separate
dimensions (company quality, price, momentum/timing, risk, decision) instead of
one Score V2 that mixes them.

Nothing here changes the live engine. It reads the current canonical rows
(stockdata.load_rows), the fresh fundamentals + analyst targets saved in
research/decision_structure_inputs.json, and compares:

  A. the live verdicts (Score V2 as-is),
  B. Score V2 with the technical weight at 10% and at 0% (renormalised),
  C. a business-only quality score (fundamental_score without PEG / forward P/E),
  D. the proposed five-dimension decision (and a variant that also lets a fair
     company at an attractive price through).

Usage:  python research/decision_structure_study.py
Output: research/decision_structure_results.json + a printed summary.
"""
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

import stockdata                                    # noqa: E402
import verdict as V                                 # noqa: E402
from decisions import valuation_score               # noqa: E402
from ranking_engine.factor_scores import fundamental_score   # noqa: E402

INPUTS = os.path.join(_HERE, "decision_structure_inputs.json")
OUT = os.path.join(_HERE, "decision_structure_results.json")
BASE_W = {"fundamental": 0.35, "technical": 0.25, "sector": 0.20, "news": 0.10, "risk": 0.10}


def _n(v):
    return v if isinstance(v, (int, float)) and v == v else None


def v2(r, tech_w=0.25):
    """Score V2 with a chosen technical weight, the rest renormalised as in composite.py."""
    w = dict(BASE_W, technical=tech_w)
    risk = _n(r.get("ScoreRisk")) if _n(r.get("ScoreRisk")) is not None else _n(r.get("RiskScore"))
    sector = _n(r.get("SectorScore"))
    if sector is None and _n(r.get("ContribSector")) is not None and _n(r.get("Completeness")) == 100:
        sector = r["ContribSector"] / BASE_W["sector"]     # results.csv keeps only the contribution
    raw = {"fundamental": _n(r.get("ScoreFundamental")), "technical": _n(r.get("Score")),
           "sector": sector, "news": _n(r.get("ScoreNews")) or 50.0,
           "risk": None if risk is None else max(0.0, min(100.0, 100.0 - risk))}
    avail = {k: v for k, v in raw.items() if v is not None and w[k] > 0}
    tot = sum(w[k] for k in avail)
    return round(sum(v * w[k] / tot for k, v in avail.items())) if tot else None


def business_quality(fund):
    """fundamental_score on growth, margins, ROIC, FCF and debt only: price multiples removed."""
    f = {k: v for k, v in (fund or {}).items() if k not in ("PEG", "ForwardPE")}
    return fundamental_score(f)


def spearman(a, b):
    keys = [k for k in a if a[k] is not None and b.get(k) is not None]
    def ranks(d):
        order = sorted(keys, key=lambda k: d[k])
        return {k: i for i, k in enumerate(order)}
    ra, rb = ranks(a), ranks(b)
    n = len(keys)
    d2 = sum((ra[k] - rb[k]) ** 2 for k in keys)
    return round(1 - 6 * d2 / (n * (n * n - 1)), 3) if n > 2 else None


def top_overlap(a, b, k=10):
    ta = set(sorted((t for t in a if a[t] is not None), key=lambda t: -a[t])[:k])
    tb = set(sorted((t for t in b if b[t] is not None), key=lambda t: -b[t])[:k])
    return len(ta & tb)


# ------------------------------------------------------------------ dimensions
def price_dim(fund, price, target, analysts):
    """Price attractiveness: multiples (PEG + forward P/E) and the analyst consensus.
    Never 'attractive' or 'fair' when the price is already above the consensus target."""
    val = valuation_score(fund) if fund else None
    up = round((target / price - 1) * 100, 1) if target and price else None
    use_target = up is not None and (analysts or 0) >= 5
    up_score = max(0.0, min(100.0, 50 + 2.5 * up)) if use_target else None
    parts = [x for x in (val, up_score) if x is not None]
    score = round(sum(parts) / len(parts)) if parts else None
    if score is None:
        label = None
    elif score >= 65:
        label = "attractive"
    elif score >= 50:
        label = "fair"
    elif score >= 35:
        label = "full"
    else:
        label = "expensive"
    if use_target and up < 0 and label in ("attractive", "fair"):
        label = "full"
    return {"score": score, "label": label, "valuation": val, "upside": up}


def timing_dim(f):
    trend = V._trend(f)
    stretched = (_n(f.get("rsi")) or 0) >= 75
    return {"trend": trend, "technical": _n(f.get("technical")), "stretched": stretched}


def risk_dim(f):
    lvl = f.get("risk_level")
    very_high = lvl == "גבוה מאוד"
    earnings = _n(f.get("days_to_earnings"))
    return {"level": lvl, "very_high": very_high,
            "earnings_soon": earnings is not None and 0 <= earnings <= 7}


def decide5(q, p, t, r, allow_fair_value=False):
    """The proposed decision. Returns (action, reason_key)."""
    tier = V._quality_tier(q)
    if tier is None:
        return "nodata", "no_quality"
    if tier == "poor":
        return "avoid", "weak_business"
    if t["trend"] == "down" and tier != "strong":
        return "avoid", "downtrend_not_strong"
    if r["very_high"] and tier != "strong":
        return "avoid", "risk_not_strong"
    good_price = p["label"] in ("attractive", "fair")
    if tier == "strong":
        if t["trend"] == "down":
            return "wait", "strong_downtrend"
        if r["very_high"]:
            return "wait", "strong_very_high_risk"
        if not good_price:
            return "wait", "strong_full_price" if p["label"] else "strong_no_price"
        return "buy", "strong_good_price"
    if (allow_fair_value and tier == "fair" and p["label"] == "attractive"
            and t["trend"] == "up" and r["level"] in ("נמוך", "בינוני")):
        return "buy", "fair_attractive_price"
    return "wait", "not_strong_enough"


def main():
    inp = json.load(open(INPUTS, encoding="utf-8"))
    rows = stockdata.load_rows()
    tick = [t for t, r in rows.items() if r.get("_tier") in ("full", "enriched")]
    tgt, fund = inp["targets"], inp["fundamentals"]

    scores = {"v2_live": {}, "v2_tech10": {}, "v2_tech0": {}, "business": {}}
    verdicts = {"live": {}, "v2_tech10": {}, "v2_tech0": {}, "business_only_q": {}}
    shadow, shadow_b, detail = {}, {}, {}
    for t in tick:
        r = rows[t]
        scores["v2_live"][t] = _n(r.get("ScoreV2"))
        scores["v2_tech10"][t] = v2(r, 0.10)
        scores["v2_tech0"][t] = v2(r, 0.0)
        bq = business_quality(fund.get(t))
        scores["business"][t] = bq
        verdicts["live"][t] = V.verdict_for_row(r)["action"]
        for name, q in (("v2_tech10", scores["v2_tech10"][t]), ("v2_tech0", scores["v2_tech0"][t]),
                        ("business_only_q", bq)):
            verdicts[name][t] = V.verdict_for_row(dict(r, ScoreV2=q))["action"]

        f = V.features_from_row(r)
        tg = tgt.get(t) or {}
        price_now = _n(tg.get("PriceNow")) or f["price"]
        p = price_dim(fund.get(t), price_now, _n(tg.get("TargetMean")), _n(tg.get("AnalystCount")))
        tm, rk = timing_dim(f), risk_dim(f)
        shadow[t] = decide5(bq, p, tm, rk)
        shadow_b[t] = decide5(bq, p, tm, rk, allow_fair_value=True)
        detail[t] = {"v2": scores["v2_live"][t], "business_q": bq,
                     "q_tier_live": V._quality_tier(scores["v2_live"][t]), "q_tier_business": V._quality_tier(bq),
                     "price": p, "price_now": price_now, "target": _n(tg.get("TargetMean")),
                     "analysts": _n(tg.get("AnalystCount")), "timing": tm, "risk": rk,
                     "live": verdicts["live"][t], "proposed": shadow[t][0], "proposed_reason": shadow[t][1],
                     "proposed_b": shadow_b[t][0]}

    def changes(a, b):
        return sorted(f"{t}: {a[t]}→{b[t]}" for t in tick if a[t] != b[t])

    proposed = {t: a for t, (a, _) in shadow.items()}
    proposed_b = {t: a for t, (a, _) in shadow_b.items()}
    res = {
        "as_of": {"rows": rows[tick[0]].get("Date"), "fundamentals_targets": inp.get("fetched")},
        "n": len(tick),
        "rank_vs_live": {k: {"spearman": spearman(scores["v2_live"], s), "top10_overlap": top_overlap(scores["v2_live"], s)}
                         for k, s in scores.items() if k != "v2_live"},
        # What actually orders Score V2: rank correlation with each input.
        "v2_rank_drivers": {k: spearman(scores["v2_live"], {t: _n(rows[t].get(col)) for t in tick})
                            for k, col in (("fundamental", "ScoreFundamental"), ("technical", "Score"),
                                           ("sector", "SectorScore"), ("risk", "RiskScore"))},
        "quality_tiers": {k: dict(Counter(V._quality_tier(v) for v in s.values())) for k, s in scores.items()},
        "actions": {**{k: dict(Counter(v.values())) for k, v in verdicts.items()},
                    "proposed": dict(Counter(proposed.values())), "proposed_b": dict(Counter(proposed_b.values()))},
        "changes_vs_live": {**{k: changes(verdicts["live"], v) for k, v in verdicts.items() if k != "live"},
                            "proposed": changes(verdicts["live"], proposed),
                            "proposed_b": changes(verdicts["live"], proposed_b)},
        "proposed_reasons": dict(Counter(r for _, r in shadow.values())),
        "price_labels": dict(Counter(d["price"]["label"] for d in detail.values())),
        "live_buys_above_target": sorted(t for t in tick if verdicts["live"][t] == "buy"
                                         and (detail[t]["price"]["upside"] or 0) < 0),
        "detail": detail,
    }
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k in ("n", "rank_vs_live", "v2_rank_drivers", "quality_tiers", "actions", "proposed_reasons", "price_labels",
              "live_buys_above_target", "changes_vs_live"):
        print(k, json.dumps(res[k], ensure_ascii=False))


if __name__ == "__main__":
    main()
