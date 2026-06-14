# -*- coding: utf-8 -*-
"""Structured, plain-Hebrew explanations per stock (Phase 5).

Generates Why-Buy / Why-Watch / Why-Avoid bullet lists plus Key Catalysts and
Key Risks — all rule-based from REAL data (the scan metrics + optional events
and sector context). Nothing fabricated; reasons map directly to real signals.
"""
from ranking_engine.interpret import classify


def explain(row, events: dict | None = None, sector: dict | None = None) -> dict:
    """Return {why_buy, why_watch, why_avoid, catalysts, risks} lists (Hebrew)."""
    events = events or {}
    g = classify(row)["group"]

    price = row.get("Price", 0)
    ma50, ma200 = row.get("MA50", 0), row.get("MA200", 0)
    rsi = row.get("RSI14", 50)
    vr = row.get("VolRatio", 1)
    dist = row.get("DistFromHigh%", 100)
    fund = row.get("ScoreFundamental")
    risk_level = row.get("RiskLevel", "בינוני")

    why_buy, why_watch, why_avoid, catalysts, risks = [], [], [], [], []

    # --- Positive factors (why buy) ---
    if price > ma200:
        why_buy.append("מעל ממוצע 200 יום — מגמה ארוכת טווח חיובית")
    if price > ma50:
        why_buy.append("מעל ממוצע 50 יום — מגמה בינונית חיובית")
    if 50 <= rsi <= 75:
        why_buy.append(f"RSI {rsi} — מומנטום בריא (לא קנוי יתר)")
    if vr >= 1.5:
        why_buy.append(f"נפח מסחר פי {vr} מהרגיל — עניין ער")
    if dist <= 5:
        why_buy.append("קרוב מאוד לשיא 52 השבועות — חוזק")
    if isinstance(fund, (int, float)) and fund >= 65:
        why_buy.append(f"ציון פונדמנטלי גבוה ({int(fund)})")

    # --- Mixed signals (why watch) ---
    if 40 <= rsi < 50:
        why_watch.append(f"RSI {rsi} — ניטרלי, מחכה לכיוון")
    if 5 < dist <= 12:
        why_watch.append(f"{dist}% מתחת לשיא — לא רחוק אך לא פורץ")
    if 1.0 <= vr < 1.5:
        why_watch.append("נפח סביב הממוצע — אין הכרעה")

    # --- Negative factors (why avoid) ---
    if price < ma200:
        why_avoid.append("מתחת לממוצע 200 יום — מגמה ארוכת טווח שלילית")
    if price < ma50:
        why_avoid.append("מתחת לממוצע 50 יום — חולשה בינונית")
    if rsi < 40:
        why_avoid.append(f"RSI {rsi} — מומנטום חלש")
    if dist > 20:
        why_avoid.append(f"{dist}% מתחת לשיא — רחוק מאוד מהשיא")

    # --- Catalysts (real upcoming/positive triggers) ---
    if row.get("Breakout"):
        catalysts.append("🚀 פריצה טכנית מעל התנגדות בנפח גבוה")
    if vr >= 2:
        catalysts.append(f"📊 זינוק נפח חריג (פי {vr})")
    if events.get("days_to_earnings") is not None and events["days_to_earnings"] <= 14:
        catalysts.append(f"📅 דוחות כספיים בעוד {events['days_to_earnings']} ימים "
                         f"({events.get('earnings_date','')})")
    if events.get("rating_action") and "שדרוג" in str(events["rating_action"]):
        catalysts.append(f"⬆️ שדרוג אנליסטים — {events['rating_firm'] or ''} "
                         f"({events['rating_action']})")
    if sector and sector.get("score", 0) >= 70:
        catalysts.append(f"🔥 סקטור חזק: {sector['sector']} (ציון {sector['score']})")

    # --- Risks (real warning signals) ---
    if rsi >= 75:
        risks.append(f"⚠️ RSI {rsi} — קנוי יתר, סיכון לתיקון")
    if price < ma200:
        risks.append("⚠️ מתחת לממוצע 200 — מגמה שלילית")
    if risk_level == "גבוה":
        risks.append("⚠️ תנודתיות גבוהה (רמת סיכון גבוהה)")
    if events.get("days_to_earnings") is not None and events["days_to_earnings"] <= 7:
        risks.append(f"⚠️ דוחות בעוד {events['days_to_earnings']} ימים — סיכון אירוע")
    if events.get("rating_action") and "הורדת" in str(events["rating_action"]):
        risks.append(f"⚠️ הורדת דירוג — {events['rating_firm'] or ''}")
    if sector and sector.get("score", 100) < 35:
        risks.append(f"⚠️ סקטור חלש: {sector['sector']} (ציון {sector['score']})")

    # Friendly fallbacks so nothing is empty (Phase 10).
    if not why_buy:
        why_buy.append("אין כרגע גורמים חיוביים בולטים.")
    if not risks:
        risks.append("לא זוהו סיכונים חריגים כרגע.")
    if not catalysts:
        catalysts.append("אין קטליזטור קרוב מזוהה.")

    return {"why_buy": why_buy, "why_watch": why_watch, "why_avoid": why_avoid,
            "catalysts": catalysts, "risks": risks, "group": g}
