# -*- coding: utf-8 -*-
"""AI Insights (Phase 11) — daily Hebrew narrative, rule-based (no paid LLM).

Turns the day's computed data (market overview, scan groups, alerts, sectors)
into a readable Hebrew briefing: market summary, best opportunities, biggest
risks, and sector rotation. Deterministic and transparent — every sentence
maps to real numbers already shown elsewhere in the app.
"""
from ranking_engine.interpret import classify


def generate_insights(market: dict, df, alert_center: list) -> dict:
    """Return {summary, market, opportunities, risks, rotation} Hebrew strings."""
    regime = market.get("regime", {})
    fng = market.get("fear_greed", {})
    breadth = market.get("breadth", {})
    sectors = market.get("sectors", [])
    indices = {ix["name"]: ix for ix in market.get("indices", [])}

    groups = df.assign(_g=[classify(r)["group"] for _, r in df.iterrows()])
    positive = groups[groups["_g"] == "positive"].sort_values("Score", ascending=False)
    avoid = groups[groups["_g"] == "avoid"]
    n_break = int(df["Breakout"].sum())

    def idx(name):
        ix = indices.get(name, {})
        cp = ix.get("change_pct")
        return f"{name} {'+' if (cp or 0) >= 0 else ''}{cp}%" if cp is not None else name

    # --- Market summary ---
    market_txt = (
        f"השוק במצב **{regime.get('label','—')}** ({regime.get('score','—')}/100). "
        f"מד הפחד/חמדנות: {fng.get('score','—')} ({fng.get('label','—')}). "
        f"רוחב שוק: {breadth.get('above50','—')}% מהמניות מעל ממוצע 50 יום. "
        f"מדדים: {idx('S&P 500')} · {idx('NASDAQ')} · {idx('Russell 2000')}."
    )

    # --- Best opportunities ---
    if positive.empty:
        opp_txt = "אין היום מניות במומנטום חיובי בולט — שוק זהיר."
    else:
        items = []
        for _, r in positive.head(3).iterrows():
            info = classify(r)
            items.append(f"**{r['Ticker']}** ({info['label']}, ציון {int(r['Score'])}, "
                         f"פוטנציאל {r.get('ExpectedUpside%','?')}%)")
        opp_txt = (f"{len(positive)} מניות במומנטום חיובי, מתוכן {n_break} מועמדות לפריצה. "
                   f"הבולטות: " + " · ".join(items) + ".")

    # --- Biggest risks (genuine risk alerts only — exclude positive breakouts) ---
    risk_alerts = [a for a in (alert_center or [])
                   if a.get("type") in ("אזהרת סיכון", "דוחות")
                   or (a.get("type") == "שינוי דירוג" and a.get("severity") == "גבוהה")]
    risk_bits = [f"{len(avoid)} מניות בסטטוס 'להימנעות'"]
    if risk_alerts:
        risk_bits.append(f"{len(risk_alerts)} התראות סיכון/אירוע")
        risk_bits.append("בולטת: " + risk_alerts[0]["message"])
    risks_txt = ". ".join(risk_bits) + "."

    # --- Sector rotation ---
    if sectors and "score" in sectors[0]:
        ranked = sorted(sectors, key=lambda s: s["score"], reverse=True)
        s, w = ranked[0], ranked[-1]
        rotation_txt = (f"כניסת הון אל **{s['sector']}** (ציון {s['score']}, חוזק יחסי {s['rs']:+}%); "
                        f"יציאה מ**{w['sector']}** (ציון {w['score']}, {w['rs']:+}%).")
    else:
        rotation_txt = "אין נתוני רוטציה סקטוריאלית כרגע."

    summary = (f"{regime.get('label','—')} · {len(positive)} הזדמנויות · "
               f"{len(avoid)} להימנעות · סקטור מוביל: "
               f"{(sorted(sectors, key=lambda s: s['score'], reverse=True)[0]['sector']) if sectors and 'score' in sectors[0] else '—'}.")

    return {
        "summary": summary,
        "market": market_txt,
        "opportunities": opp_txt,
        "risks": risks_txt,
        "rotation": rotation_txt,
    }
