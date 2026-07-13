# -*- coding: utf-8 -*-
"""Delta Engine (Morning Terminal) — "what changed since the previous scan?"

The platform's core morning question. Works from two committed compact
snapshots (data/scores_prev.json ← rotated ← data/scores_today.json) so it
runs identically locally AND on the cloud bot. Every score change carries its
measurable CAUSE from the composite contribution columns — never "it moved".
Pure diff/classify logic is unit-tested; run.py owns rotation.
"""
import json
import os
from datetime import datetime

import config

SCORES_TODAY = os.path.join(config.DATA_DIR, "scores_today.json")
SCORES_PREV = os.path.join(config.DATA_DIR, "scores_prev.json")

_FIELDS = ["Price", "ScoreV2", "TrustScore", "RiskLevel", "Support", "Resistance",
           "ContribFund", "ContribTech", "ContribSector", "ContribNews", "ContribRisk",
           "Breakout", "Name", "Sector"]
CONTRIB_HE = {"ContribFund": "פונדמנטלי", "ContribTech": "טכני", "ContribSector": "סקטור",
              "ContribNews": "חדשות", "ContribRisk": "בריאות-סיכון"}


def _n(v):
    return v if isinstance(v, (int, float)) and v == v else None


def compact_snapshot(df) -> dict:
    """DataFrame (EN columns) → compact per-ticker map + date stamp."""
    out = {"date": datetime.now().strftime("%d/%m/%Y"), "tickers": {}}
    for _, r in df.iterrows():
        tk = r.get("Ticker")
        if not tk:
            continue
        row = {}
        for f in _FIELDS:
            v = r.get(f)
            if isinstance(v, (int, float)) and v == v:
                row[f] = round(float(v), 2)
            elif isinstance(v, (str, bool)):
                row[f] = v
        # status label from the interpretation engine (present on the dashboard df;
        # computed on the fly in the pipeline)
        grp = r.get("_group")
        if not grp:
            try:
                from ranking_engine.interpret import classify
                grp = classify(r)["group"]
            except Exception:
                grp = None
        if grp:
            row["Group"] = grp
        out["tickers"][tk] = row
    return out


def rotate_and_write(df) -> bool:
    """Called by the pipeline: today→prev (only across different dates), write new today."""
    try:
        snap = compact_snapshot(df)
        if os.path.exists(SCORES_TODAY):
            try:
                with open(SCORES_TODAY, encoding="utf-8") as fh:
                    old = json.load(fh)
                if old.get("date") != snap["date"]:
                    with open(SCORES_PREV, "w", encoding="utf-8") as fh:
                        json.dump(old, fh, ensure_ascii=False)
            except Exception:
                pass
        with open(SCORES_TODAY, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_pair():
    def _rd(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None
    return _rd(SCORES_PREV), _rd(SCORES_TODAY)


def diff_scores(prev: dict, cur: dict, min_score_move=3.0) -> dict:
    """Pure diff → materiality-ranked delta feed with measurable causes."""
    if not prev or not cur:
        return {"available": False, "items": [], "new": [], "removed": []}
    p, c = prev.get("tickers", {}), cur.get("tickers", {})
    items = []
    for tk in set(p) & set(c):
        a, b = p[tk], c[tk]
        dv2 = (_n(b.get("ScoreV2")) - _n(a.get("ScoreV2"))
               if _n(a.get("ScoreV2")) is not None and _n(b.get("ScoreV2")) is not None else None)
        dprice = (round((b["Price"] / a["Price"] - 1) * 100, 1)
                  if _n(a.get("Price")) and _n(b.get("Price")) else None)
        changes, causes, materiality = [], [], 0.0
        if dv2 is not None and abs(dv2) >= min_score_move:
            changes.append(f"ציון V2 {a['ScoreV2']:.0f}→{b['ScoreV2']:.0f} ({dv2:+.0f})")
            movers = []
            for k, he in CONTRIB_HE.items():
                da = _n(a.get(k)); db = _n(b.get(k))
                if da is not None and db is not None and abs(db - da) >= 0.8:
                    movers.append((abs(db - da), f"{he} {db - da:+.1f}"))
            causes += [m[1] for m in sorted(movers, reverse=True)[:3]]
            materiality += abs(dv2) * 2
        if a.get("RiskLevel") != b.get("RiskLevel") and b.get("RiskLevel"):
            changes.append(f"סיכון: {a.get('RiskLevel', '—')}→{b['RiskLevel']}")
            materiality += 6
        if not a.get("Breakout") and b.get("Breakout"):
            changes.append("פריצה טכנית חדשה")
            causes.append("המחיר חצה את רמת הפריצה בנפח")
            materiality += 10
        _sr = _n(b.get("Support"))
        if _n(a.get("Support")) and _sr and abs(_sr - a["Support"]) / a["Support"] > 0.02:
            changes.append(f"תמיכה עודכנה ${a['Support']}→${_sr}")
            materiality += 2
        if dprice is not None and abs(dprice) >= 4:
            changes.append(f"מחיר {dprice:+.1f}%")
            materiality += abs(dprice)
        if changes:
            items.append({"ticker": tk, "name": b.get("Name", ""), "sector": b.get("Sector", ""),
                          "changes": changes, "causes": causes or ["שינוי שוק/מחיר"],
                          "d_score": dv2, "d_price": dprice,
                          "score_now": _n(b.get("ScoreV2")), "group": b.get("Group"),
                          "materiality": round(materiality, 1)})
    items.sort(key=lambda x: -x["materiality"])
    return {"available": True, "prev_date": prev.get("date"), "cur_date": cur.get("date"),
            "items": items, "new": sorted(set(c) - set(p)), "removed": sorted(set(p) - set(c))}


def action_for(score_now, group, d_score) -> dict:
    """ONE clear action per item (decision-first). Rule-based on existing labels."""
    if group == "avoid":
        return {"icon": "❌", "verb": "להימנע"}
    if (d_score or 0) <= -8:
        return {"icon": "⚠️", "verb": "לבחון מחדש"}
    if group == "positive" and (score_now or 0) >= 75:
        return {"icon": "📈", "verb": "לבחון צבירה"}
    if (d_score or 0) >= 8:
        return {"icon": "🔍", "verb": "לחקור היום"}
    if group == "positive":
        return {"icon": "⭐", "verb": "להוסיף למעקב"}
    return {"icon": "⏳", "verb": "להמתין"}


def classify_environment(regime: dict, vix_row: dict = None, breadth: dict = None,
                         sectors: list = None) -> dict:
    """Named market environment + the measurable WHY. Deterministic."""
    labels, why = [], []
    rs = _n((regime or {}).get("score"))
    if rs is not None:
        if rs >= 60:
            labels.append("Risk-On")
            why.append(f"ציון משטר {rs:.0f} — מדדים מעל ממוצעים ורוחב חיובי")
        elif rs < 40:
            labels.append("Risk-Off")
            why.append(f"ציון משטר {rs:.0f} — חולשה רוחבית")
        else:
            labels.append("שוק מעורב")
            why.append(f"ציון משטר {rs:.0f} — אותות סותרים")
    vix = _n((vix_row or {}).get("price"))
    if vix is not None:
        if vix >= 25:
            labels.append("תנודתיות גבוהה")
            why.append(f"VIX {vix:.0f} — מעל סף הלחץ")
        elif vix <= 15:
            labels.append("תנודתיות נמוכה")
            why.append(f"VIX {vix:.0f} — שאננות יחסית")
    b50 = _n((breadth or {}).get("above50"))
    if b50 is not None:
        why.append(f"{b50:.0f}% מהמניות מעל ממוצע 50")
        if rs is not None and rs >= 60 and b50 < 45:
            labels.append("עלייה צרה (מובלת בודדות)")
    defensive = {"שירותים ציבוריים", "צריכה בסיסית", "בריאות"}
    if sectors:
        top2 = {s.get("sector") for s in sectors[:2]}
        if top2 & defensive:
            labels.append("רוטציה דפנסיבית")
            why.append(f"סקטורים מובילים: {', '.join(top2)}")
    return {"labels": labels or ["לא ניתן לסווג"], "why": why}


def asset_flows(global_groups: dict) -> list:
    """Cross-asset 30-day trends — an ESTIMATED flow proxy (labeled), from real prices."""
    def _avg_d30(rows):
        vals = [_n(r.get("d30")) for r in rows if _n(r.get("d30")) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None
    g = global_groups or {}
    us = [r for r in g.get("equity", []) if r.get("symbol") in ("^GSPC", "^IXIC", "^DJI", "^RUT")]
    intl = [r for r in g.get("equity", []) if r.get("symbol") in ("^N225", "^GDAXI", "^FTSE", "^HSI")]
    rows = [("מניות ארה\"ב", _avg_d30(us)), ("מניות בינלאומיות", _avg_d30(intl)),
            ("קריפטו", _avg_d30(g.get("crypto", []))),
            ("סחורות", _avg_d30(g.get("commodity", []))),
            ("זהב (מגן)", _avg_d30([r for r in g.get("commodity", []) if r.get("symbol") == "GC=F"]))]
    return [{"asset": a, "d30": v,
             "trend": "↑ כניסה" if (v or 0) > 2 else "↓ יציאה" if (v or 0) < -2 else "→ יציב"}
            for a, v in rows if v is not None]
