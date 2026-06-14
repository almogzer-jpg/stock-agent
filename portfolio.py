# -*- coding: utf-8 -*-
"""Portfolio analytics (Phase 7) — pure computation over real holdings.

Holdings come from portfolio.csv (Ticker, Quantity, AverageCost). run.py fetches
each holding's live data and passes enriched position dicts here; this module
does the aggregation: P/L, weights, returns vs S&P, exposures, a 0-100 health
score, and portfolio alerts. No fabricated values.
"""
import csv
import os


def load_holdings(path: str) -> list[dict]:
    """Parse portfolio.csv → [{ticker, quantity, avg_cost}]. Robust to headers."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Accept flexible header names.
            keys = {k.strip().lower(): v for k, v in row.items() if k}
            tkr = (keys.get("ticker") or keys.get("symbol") or "").strip().upper()
            if not tkr or tkr.startswith("#"):
                continue
            try:
                qty = float(keys.get("quantity") or keys.get("qty") or 0)
                cost = float(keys.get("averagecost") or keys.get("average cost")
                             or keys.get("avg_cost") or keys.get("cost") or 0)
            except ValueError:
                continue
            if qty > 0 and cost > 0:
                out.append({"ticker": tkr, "quantity": qty, "avg_cost": cost})
    return out


def _cap_bucket(market_cap) -> str:
    if not market_cap:
        return "לא ידוע"
    if market_cap >= 10e9:
        return "Large Cap"
    if market_cap >= 2e9:
        return "Mid Cap"
    return "Small Cap"


def _health(positions, exposures) -> dict:
    """0-100 portfolio health from diversification / concentration / sizing."""
    n = len(positions)
    if n == 0:
        return {"score": None, "factors": [], "method": "אין החזקות."}
    weights = [p["weight"] / 100 for p in positions]
    hhi = sum(w * w for w in weights) or 1
    eff_n = 1 / hhi                                   # effective # of positions
    max_pos = max(p["weight"] for p in positions)
    max_sector = max(exposures["sector"].values()) if exposures["sector"] else 100
    high_risk_w = sum(p["weight"] for p in positions if p.get("risk_level") == "גבוה")

    # Diversification (30): effective positions 1→0, 8+→30.
    div = max(0, min(30, (eff_n - 1) / 7 * 30))
    # Sector concentration (25): max sector 25%→25, 60%+→0.
    sec = max(0, min(25, (60 - max_sector) / 35 * 25))
    # Risk concentration (25): 0%→25, 60%+→0.
    rsk = max(0, min(25, (60 - high_risk_w) / 60 * 25))
    # Position sizing (20): max position 20%→20, 40%+→0.
    siz = max(0, min(20, (40 - max_pos) / 20 * 20))

    score = int(round(div + sec + rsk + siz))
    return {
        "score": score,
        "factors": [
            f"פיזור אפקטיבי: {eff_n:.1f} פוזיציות",
            f"ריכוז סקטור מרבי: {max_sector:.0f}%",
            f"חשיפה לסיכון גבוה: {high_risk_w:.0f}%",
            f"פוזיציה גדולה ביותר: {max_pos:.0f}%",
        ],
        "method": "פיזור (30) + ריכוז סקטוריאלי (25) + ריכוז סיכון (25) + גודל פוזיציה (20).",
    }


def _alerts(positions, exposures) -> list[dict]:
    alerts = []
    for p in positions:
        if p["weight"] > 25:
            alerts.append({"severity": "בינונית", "scope": p["ticker"],
                           "message": f"{p['ticker']} מהווה {p['weight']:.0f}% מהתיק — מעל 25% (ריכוז יתר)"})
        if p.get("status_group") == "avoid":
            alerts.append({"severity": "גבוהה", "scope": p["ticker"],
                           "message": f"{p['ticker']} הידרדרה לסטטוס 'להימנעות' — לשקול מחדש"})
    for sector, w in exposures["sector"].items():
        if w > 40:
            alerts.append({"severity": "בינונית", "scope": sector,
                           "message": f"חשיפה של {w:.0f}% לסקטור {sector} — מעל 40% (ריכוז יתר)"})
    return alerts


def build_portfolio(positions: list[dict], benchmark: dict | None = None) -> dict:
    """Aggregate enriched positions into the full portfolio payload."""
    benchmark = benchmark or {}
    if not positions:
        return {"empty": True}

    total_mv = sum(p["quantity"] * p["price"] for p in positions if p.get("price"))
    total_cost = sum(p["quantity"] * p["avg_cost"] for p in positions)

    enriched = []
    for p in positions:
        price = p.get("price") or 0
        mv = p["quantity"] * price
        cost = p["quantity"] * p["avg_cost"]
        pl = mv - cost
        enriched.append({
            **p,
            "market_value": round(mv, 2),
            "cost_basis": round(cost, 2),
            "pl": round(pl, 2),
            "pl_pct": round((price / p["avg_cost"] - 1) * 100, 2) if p["avg_cost"] else 0,
            "weight": round(mv / total_mv * 100, 2) if total_mv else 0,
            "cap_bucket": _cap_bucket(p.get("market_cap")),
        })

    def wsum(field):
        return round(sum(p["weight"] / 100 * (p.get(field) or 0) for p in enriched), 2)

    # Exposures (weight % by group)
    def group_weight(keyfn):
        out = {}
        for p in enriched:
            k = keyfn(p) or "לא ידוע"
            out[k] = round(out.get(k, 0) + p["weight"], 1)
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    exposures = {
        "sector": group_weight(lambda p: p.get("sector")),
        "cap": group_weight(lambda p: p.get("cap_bucket")),
        "risk": group_weight(lambda p: p.get("risk_level")),
    }

    total_pl = total_mv - total_cost
    payload = {
        "empty": False,
        "positions": sorted(enriched, key=lambda p: p["market_value"], reverse=True),
        "total_value": round(total_mv, 2),
        "total_cost": round(total_cost, 2),
        "total_pl": round(total_pl, 2),
        "total_pl_pct": round(total_pl / total_cost * 100, 2) if total_cost else 0,
        "daily_change_pct": wsum("daily_change_pct"),
        "monthly_change_pct": wsum("ret_1m"),
        "ytd_pct": wsum("ret_ytd"),
        "benchmark": benchmark,        # {daily, ret_1m, ret_ytd} for S&P 500
        "exposures": exposures,
    }
    payload["health"] = _health(enriched, exposures)
    payload["alerts"] = _alerts(enriched, exposures)
    return payload
