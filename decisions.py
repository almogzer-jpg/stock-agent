# -*- coding: utf-8 -*-
"""Portfolio Decision Engine (Phase 14, Part 3).

Turns the portfolio from descriptive analytics into ACTIONS. For each holding it
derives a target allocation (0/2/5/10/15%) from the composite Final Score v2,
risk, sector strength, market regime and concentration constraints, then maps
current→target into Increase / Hold / Reduce / Exit — each fully explained
(why / supporting data / remaining risks). Also builds "What should I do today?"
sector rebalancing, risk-reduction actions, and hard constraint warnings.

All rule-based on REAL inputs — no placeholders.
"""

BUCKETS = [0, 2, 5, 10, 15]


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))


def valuation_score(fund: dict | None) -> float | None:
    """0-100 valuation (higher = better value) from PEG + Forward PE."""
    if not fund:
        return None
    peg, fpe = fund.get("PEG"), fund.get("ForwardPE")
    if not isinstance(peg, (int, float)) and not isinstance(fpe, (int, float)):
        return None
    s = 50.0
    if isinstance(peg, (int, float)) and peg > 0:
        s += 25 if peg <= 1 else (10 if peg <= 2 else -15)
    if isinstance(fpe, (int, float)) and fpe > 0:
        s += 20 if fpe <= 18 else (5 if fpe <= 30 else -15)
    return round(_clamp(s), 1)


def _risk_off(regime_label: str) -> bool:
    return bool(regime_label) and ("דובי" in regime_label or "Risk-Off" in regime_label)


def target_allocation(score_v2, risk_category, sector_score, regime_label) -> int:
    """Recommended position size bucket (%) from score/risk/sector/regime."""
    v2 = score_v2 or 0
    base = (15 if v2 >= 75 else 10 if v2 >= 65 else 5 if v2 >= 55 else 2 if v2 >= 40 else 0)
    cap = {"גבוה מאוד": 5, "גבוה": 10}.get(risk_category, 15)   # risk caps size
    base = min(base, cap)
    idx = BUCKETS.index(base)
    if sector_score is not None and sector_score < 35 and idx > 0:   # weak sector → trim
        idx -= 1
    if _risk_off(regime_label) and idx > 0:                          # defensive in risk-off
        idx -= 1
    return BUCKETS[idx]


def decide_holding(p: dict, regime_label: str) -> dict:
    """Decision for one holding: action + target + confidence + explanation."""
    v2 = p.get("score_v2") or 0
    rc = p.get("risk_level") or "בינוני"
    ss = p.get("sector_score")
    cur = round(p.get("weight", 0), 1)
    target = target_allocation(v2, rc, ss, regime_label)
    gap = target - cur

    if target == 0:
        action = "Exit"
    elif gap > 2:
        action = "Increase"
    elif gap < -2:
        action = "Reduce"
    else:
        action = "Hold"

    # Why (supporting data)
    why = [f"ציון סופי v2 {int(v2)}"]
    if ss is not None:
        why.append(f"חוזק סקטור {int(ss)}")
    why.append(f"סיכון {rc}")
    if p.get("valuation") is not None:
        why.append(f"שווי {int(p['valuation'])}")

    # Remaining risks
    risks = []
    if rc in ("גבוה", "גבוה מאוד"):
        risks.append(f"רמת סיכון {rc}")
    if isinstance(p.get("beta"), (int, float)) and p["beta"] > 1.3:
        risks.append(f"ביתא גבוהה {p['beta']}")
    if cur > 20:
        risks.append(f"פוזיציה גדולה ({cur}%)")
    if not risks:
        risks.append("ללא סיכון חריג")

    verb = {"Increase": "הגדלה", "Reduce": "הקטנה", "Exit": "יציאה", "Hold": "החזקה"}[action]
    reasoning = (f"יעד מומלץ {target}% מול {cur}% נוכחי → {verb}. "
                 f"מבוסס על: {', '.join(why)}.")

    # Decision confidence: holding confidence blended with action clarity (gap size)
    base_conf = p.get("confidence") or 50
    clarity = _clamp(abs(gap) / 10 * 100) if action != "Hold" else 70
    confidence = int(round(0.6 * base_conf + 0.4 * clarity))

    # Priority
    violates = cur > 20
    if action == "Exit" or violates:
        priority = "גבוהה"
    elif abs(gap) >= 5:
        priority = "בינונית"
    else:
        priority = "נמוכה"

    # Expected risk impact
    high_risk = rc in ("גבוה", "גבוה מאוד")
    if action in ("Reduce", "Exit"):
        impact = "מפחית סיכון תיק" if high_risk else "מפחית חשיפה"
    elif action == "Increase":
        impact = "מעלה סיכון תיק" if high_risk else "מעלה חשיפה, סיכון מתון"
    else:
        impact = "ניטרלי"

    return {
        "ticker": p["ticker"], "name": p.get("name", ""),
        "action": action, "current_pct": cur, "target_pct": target,
        "confidence": confidence, "risk_level": rc, "score_v2": int(v2),
        "valuation": p.get("valuation"), "sector_score": ss,
        "priority": priority, "risk_impact": impact,
        "reasoning": reasoning, "why": why, "risks": risks,
    }


def portfolio_decisions(positions, sectors_all, regime_label, prisk, correlation) -> dict:
    """Full decision payload: per-holding decisions + today's actions +
    rebalancing + risk-reduction + hard constraint warnings."""
    holdings = [decide_holding(p, regime_label) for p in positions]

    # Held-sector aggregation: weight + score per (English) sector.
    held = {}
    for p in positions:
        sec = p.get("sector") or "לא ידוע"
        held.setdefault(sec, {"weight": 0.0, "score": p.get("sector_score")})
        held[sec]["weight"] += p.get("weight", 0)

    overweight, underweight, rebal_actions = [], [], []
    for sec, d in sorted(held.items(), key=lambda kv: -kv[1]["weight"]):
        w, sc = round(d["weight"], 1), d["score"]
        if w > 35:
            overweight.append({"sector": sec, "weight": w, "reason": "מעל מגבלת 35%"})
            rebal_actions.append(f"הקטן חשיפה ל{sec} (כעת {w}%, מעל מגבלת 35%)")
        elif sc is not None and sc < 35 and w >= 10:
            overweight.append({"sector": sec, "weight": w, "reason": f"סקטור חלש (ציון {sc})"})
            rebal_actions.append(f"הקטן חשיפה ל{sec} — סקטור חלש (ציון {sc})")

    # Underweight: strong sectors (from global intelligence) barely held.
    held_weight = {s: d["weight"] for s, d in held.items()}
    from market import SECTOR_EN_TO_HE
    he_to_en = {v: k for k, v in SECTOR_EN_TO_HE.items()}
    for s in sorted(sectors_all or [], key=lambda x: -x.get("score", 0))[:3]:
        en = he_to_en.get(s["sector"])
        cur_w = held_weight.get(en, 0)
        if s.get("score", 0) >= 65 and cur_w < 10:
            underweight.append({"sector": s["sector"], "score": s["score"], "weight": round(cur_w, 1)})
            rebal_actions.append(f"שקול הגדלת חשיפה ל{s['sector']} — סקטור חזק (ציון {s['score']}), "
                                 f"כעת רק {cur_w:.0f}% בתיק")

    # Risk-reduction actions
    risk_actions = []
    if prisk.get("weighted_beta", 0) and prisk["weighted_beta"] > 1.2:
        hi = [h["ticker"] for h in holdings if h["risk_level"] in ("גבוה", "גבוה מאוד")]
        risk_actions.append(f"ביתא תיק {prisk['weighted_beta']} > 1.2 — שקול להקטין פוזיציות בסיכון גבוה"
                            + (f": {', '.join(hi)}" if hi else ""))
    for pair in (correlation or {}).get("high_pairs", []):
        risk_actions.append(f"קורלציה גבוהה {pair['a']}–{pair['b']} ({pair['corr']}) — ריכוז סמוי, שקול לדלל אחת")

    # Hard constraint warnings
    constraints = []
    for p in positions:
        if p.get("weight", 0) > 20:
            constraints.append(f"⚠️ פוזיציה בודדת: {p['ticker']} {p['weight']:.0f}% (> 20%)")
    for sec, d in held.items():
        if d["weight"] > 35:
            constraints.append(f"⚠️ סקטור {sec} {d['weight']:.0f}% (> 35%)")
    if prisk.get("weighted_beta", 0) and prisk["weighted_beta"] > 1.2:
        constraints.append(f"⚠️ ביתא תיק {prisk['weighted_beta']} (> 1.2)")
    for pair in (correlation or {}).get("high_pairs", []):
        constraints.append(f"⚠️ אשכול מתואם: {pair['a']}–{pair['b']} ({pair['corr']})")

    # "What should I do today?" — prioritized position actions + rebalancing + guardrails
    today = []
    for h in sorted(holdings, key=lambda x: {"גבוהה": 0, "בינונית": 1, "נמוכה": 2}[x["priority"]]):
        if h["action"] == "Exit":
            today.append(f"🔴 צא מ{h['ticker']} (ציון v2 {h['score_v2']}, {h['risk_impact']})")
        elif h["action"] == "Increase":
            today.append(f"🟢 הגדל {h['ticker']} ל‑{h['target_pct']}% (כעת {h['current_pct']}%)")
        elif h["action"] == "Reduce":
            today.append(f"🟡 הקטן {h['ticker']} ל‑{h['target_pct']}% (כעת {h['current_pct']}%)")
    today += rebal_actions
    if _risk_off(regime_label):
        today.append("⚠️ שוק במצב Risk-Off — הימנע מפתיחת פוזיציות חדשות בסיכון גבוה")

    return {
        "holdings": holdings,
        "today": today,
        "overweight_sectors": overweight,
        "underweight_sectors": underweight,
        "rebalancing_actions": rebal_actions,
        "risk_actions": risk_actions,
        "constraints": constraints,
    }
