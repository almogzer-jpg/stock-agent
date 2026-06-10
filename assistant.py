# -*- coding: utf-8 -*-
"""Free, rule-based Q&A assistant over the scan results (Hebrew).

No paid API and no model — it understands a set of Hebrew intents and answers
straight from the latest scan DataFrame (and optional market data). Returns
Markdown so the dashboard chat can render bullet lists nicely.
"""
import re

from ranking_engine.interpret import classify


def _stock_detail(r) -> str:
    """Full one-stock answer (status, score, price, risk, reasons)."""
    info = classify(r)
    chg = r["DailyChange%"]
    return (
        f"**{info['emoji']} {r['Ticker']} — {r['Name']}**  \n"
        f"סטטוס: {info['label']} · ציון **{int(r['Score'])}/100** · "
        f"מחיר ${r['Price']} ({'+' if chg >= 0 else ''}{chg}%) · רמת סיכון: {r['RiskLevel']}  \n"
        f"**שורה תחתונה:** {info['summary']}  \n"
        f"_{info['detail']}_"
    )


def _list(frame, n: int = 10) -> str:
    """Bullet list of stocks (symbol, name, score, one-liner)."""
    if frame.empty:
        return "_אין מניות מתאימות כרגע._"
    lines = []
    for _, r in frame.head(n).iterrows():
        info = classify(r)
        chg = r["DailyChange%"]
        lines.append(f"- {info['emoji']} **{r['Ticker']}** ({r['Name']}) · "
                     f"ציון {int(r['Score'])} · {'+' if chg >= 0 else ''}{chg}% · {info['summary']}")
    return "\n".join(lines)


def _find_tickers(question: str, df) -> list:
    """Return tickers mentioned in the question (by symbol or company name)."""
    low = question.lower()
    found = []
    for _, r in df.iterrows():
        sym = str(r["Ticker"]).lower()
        name0 = str(r["Name"]).lower().replace(",", " ").split()[0] if r["Name"] else ""
        if re.search(rf"(?<![a-z]){re.escape(sym)}(?![a-z])", low) or \
           (len(name0) >= 4 and name0 in low):
            found.append(r["Ticker"])
    return found


def _market_answer(market) -> str:
    if not market:
        return "אין כרגע נתוני שוק זמינים."
    reg = market.get("regime", {})
    parts = [f"**מצב שוק:** {reg.get('score','-')}/100 — {reg.get('label','')}"]
    for ix in market.get("indices", []):
        cp = ix.get("change_pct")
        if cp is None:
            continue
        parts.append(f"- {ix['name']}: {ix.get('price','-')} ({'+' if cp >= 0 else ''}{cp}%)")
    return "  \n".join(parts)


HELP = (
    "אני עונה על שאלות לגבי תוצאות הסריקה. נסה למשל:  \n"
    "- *מה המניות הכי חזקות?*  \n"
    "- *מה הציון של NVDA?*  \n"
    "- *כמה מועמדות לפריצה?*  \n"
    "- *למה להימנע מ-META?*  \n"
    "- *אילו מניות מעל ממוצע 200?*  \n"
    "- *מה מצב השוק?*"
)


def answer(question: str, df, market=None) -> str:
    """Route a Hebrew question to an answer built from the scan data."""
    q = (question or "").strip()
    low = q.lower()
    if not q:
        return HELP

    g = df.assign(_g=[classify(r)["group"] for _, r in df.iterrows()])
    positive = g[g["_g"] == "positive"]
    watch = g[g["_g"] == "watch"]
    avoid = g[g["_g"] == "avoid"]
    breakouts = df[df["Breakout"] == True]  # noqa: E712

    # 1) Specific stock(s) mentioned -> detailed answer.
    tickers = _find_tickers(q, df)
    if tickers:
        return "\n\n".join(_stock_detail(df[df["Ticker"] == t].iloc[0]) for t in tickers[:3])

    # 2) Market questions.
    if any(w in q for w in ["מצב שוק", "השוק", "מדד", "מאקרו"]) or \
       any(w in low for w in ["s&p", "nasdaq", "vix", "market"]):
        return _market_answer(market)

    # 3) Counting questions ("כמה ...").
    if "כמה" in q:
        if "פריצה" in q:
            return f"יש **{len(breakouts)}** מועמדות לפריצה היום: {', '.join(breakouts['Ticker']) or '—'}."
        if any(w in q for w in ["מומלצ", "חיובי", "חזק"]):
            return f"יש **{len(positive)}** מניות במומנטום חיובי."
        if "מעקב" in q:
            return f"יש **{len(watch)}** מניות למעקב."
        if any(w in q for w in ["הימנע", "חלש", "להימנע"]):
            return f"יש **{len(avoid)}** מניות להימנעות."
        return (f"נסרקו **{len(df)}** מניות: 🟢 {len(positive)} חיוביות · "
                f"🟡 {len(watch)} למעקב · 🔴 {len(avoid)} להימנעות.")

    # 4) Breakouts.
    if "פריצה" in q:
        return f"🚀 **מועמדות לפריצה ({len(breakouts)}):**  \n{_list(breakouts)}"

    # 5) Strongest / recommended / top.
    if any(w in q for w in ["הכי חזק", "חזקות", "מוביל", "מומלצ", "הכי טוב", "מנצח"]) or \
       any(w in low for w in ["top", "best", "strong"]):
        return f"🟢 **המניות החזקות ביותר:**  \n{_list(positive.sort_values('Score', ascending=False))}"

    # 6) Avoid / weak.
    if any(w in q for w in ["הימנע", "להימנע", "חלש", "גרוע", "לא טוב"]):
        return f"🔴 **מניות להימנעות ({len(avoid)}):**  \n{_list(avoid)}"

    # 7) Watch.
    if "מעקב" in q:
        return f"🟡 **מניות למעקב ({len(watch)}):**  \n{_list(watch)}"

    # 8) RSI extremes.
    if any(w in q for w in ["קנוי", "קנויות יתר", "overbought"]):
        ob = df[df["RSI14"] >= 70].sort_values("RSI14", ascending=False)
        return f"מניות בקנייתיתר (RSI≥70):  \n{_list(ob)}"
    if any(w in q for w in ["מכור", "oversold"]):
        os_ = df[df["RSI14"] <= 30].sort_values("RSI14")
        return f"מניות במכירת יתר (RSI≤30):  \n{_list(os_)}"

    # 9) Above / below 200-day MA.
    if "ממוצע 200" in q or "200" in q:
        if "מתחת" in q:
            sel = df[df["Price"] < df["MA200"]]
            return f"מתחת לממוצע 200 ({len(sel)}):  \n{_list(sel)}"
        sel = df[df["Price"] > df["MA200"]]
        return f"מעל ממוצע 200 ({len(sel)}):  \n{_list(sel)}"

    # 10) Volume.
    if "נפח" in q:
        hv = df[df["VolRatio"] >= 1.5].sort_values("VolRatio", ascending=False)
        return f"מניות בנפח מסחר גבוה (פי 1.5+):  \n{_list(hv)}"

    # 11) Risk.
    if "סיכון" in q:
        if any(w in q for w in ["נמוך", "בטוח"]):
            sel = df[df["RiskLevel"] == "נמוך"]
            return f"מניות בסיכון נמוך:  \n{_list(sel)}"
        sel = df[df["RiskLevel"] == "גבוה"]
        return f"מניות בסיכון גבוה:  \n{_list(sel)}"

    # Fallback.
    return "לא הבנתי את השאלה במדויק 🤔  \n" + HELP
