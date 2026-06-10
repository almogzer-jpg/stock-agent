# -*- coding: utf-8 -*-
"""Plain-Hebrew interpretation of a stock's metrics.

Turns the raw numbers into something a human can read at a glance: a colored
status (🟢/🟡/🔴), a one-line bottom line, and a detailed plain-language
breakdown. Used by BOTH the email report and the dashboard so the wording
stays consistent (single source of truth).
"""

# Status colors (used for HTML/email styling).
COLORS = {
    "positive": "#1b7f3b",   # green
    "watch": "#b8860b",      # amber
    "avoid": "#b3333b",      # red
}


def classify(m: dict) -> dict:
    """Return an interpretation dict for one stock's metrics.

    Keys returned:
        group   : 'positive' | 'watch' | 'avoid'  (for grouping/sorting)
        emoji   : 🟢 / 🟡 / 🔴
        label   : short Hebrew status label
        color   : hex color matching the group
        summary : one-line bottom line in plain Hebrew
        detail  : longer " · "-joined plain-Hebrew breakdown of the facts
    """
    price, ma50, ma200 = m["Price"], m["MA50"], m["MA200"]
    rsi, vr, dist = m["RSI14"], m["VolRatio"], m["DistFromHigh%"]
    score = m["Score"]
    breakout = bool(m["Breakout"])

    # --- Build the plain-language fact list -----------------------------
    facts = []
    facts.append("מעל ממוצע 200 יום — מגמה ארוכת טווח חיובית"
                 if price > ma200 else
                 "מתחת לממוצע 200 יום — מגמה ארוכת טווח שלילית")
    facts.append("מעל ממוצע 50 יום" if price > ma50 else "מתחת לממוצע 50 יום")

    if rsi >= 75:
        facts.append(f"RSI {rsi} — קנוי יתר, זהירות")
    elif rsi >= 50:
        facts.append(f"RSI {rsi} — מומנטום חיובי")
    elif rsi >= 40:
        facts.append(f"RSI {rsi} — ניטרלי-חלש")
    else:
        facts.append(f"RSI {rsi} — חלש")

    if vr >= 1.5:
        facts.append(f"נפח מסחר פי {vr} מהרגיל — עניין ער")
    elif vr >= 1.0:
        facts.append(f"נפח סביב הממוצע (x{vr})")
    else:
        facts.append(f"נפח נמוך מהרגיל (x{vr})")

    facts.append("בשיא 52 השבועות" if dist <= 0.1
                 else f"{dist}% מתחת לשיא 52 השבועות")

    detail = " · ".join(facts)

    # --- Decide the status ----------------------------------------------
    if breakout:
        group, emoji, label = "positive", "🟢", "מועמדת לפריצה"
        summary = "מומנטום חיובי חזק — פורצת קרוב לשיא בנפח מסחר גבוה."
    elif price > ma200 and price > ma50 and score >= 65:
        group, emoji, label = "positive", "🟢", "מגמה חזקה"
        summary = "במגמת עלייה בריאה, מעל הממוצעים החשובים."
    elif price < ma200 or rsi < 40 or score < 35:
        group, emoji, label = "avoid", "🔴", "להימנעות"
        summary = "חלשה כרגע — לא בכיוון חיובי, עדיף להימנע."
    else:
        group, emoji, label = "watch", "🟡", "למעקב"
        summary = "תמונה מעורבת — שווה לעקוב, בלי להיחפז."

    return {
        "group": group,
        "emoji": emoji,
        "label": label,
        "color": COLORS[group],
        "summary": summary,
        "detail": detail,
    }
