# -*- coding: utf-8 -*-
"""Alerts screen view model (V4). Pure functions, no Streamlit, so they are tested.

Alerts come from the daily scan (alerts/center.py, data/alerts_center.json) and cover
the system's fixed watchlist and the sectors. Each alert is information, not advice:
the tag beside it is the stock's current investment assessment from the live engine,
the same one every other screen shows.
"""
from datetime import datetime

from dashboard.v4 import home_data as H

_n = H._n

GROUPS = (("critical", "קריטי", "דורש תשומת לב עכשיו"),
          ("important", "חשוב", "כדאי לדעת לפני שמחליטים"),
          ("info", "מידע", "רקע, בלי צורך בפעולה"))
SEVERITY = {"גבוהה": "critical", "בינונית": "important", "מידע": "info"}
RULES = (
    ("אזהרת סיכון", "קריטי", "רמת הסיכון של המניה \"גבוה\" והמחיר מתחת לממוצע של 200 יום."),
    ("שינוי דירוג", "קריטי בהורדה, מידע בשדרוג או בכיסוי חדש", "בית השקעות שינה המלצה ב-14 הימים האחרונים. אישרור של המלצה קיימת לא נחשב התראה."),
    ("זינוק נפח", "חשוב", "נפח המסחר ביום האחרון גדול פי 2 ומעלה מהממוצע של 20 הימים."),
    ("דוחות", "חשוב", "דוח כספי צפוי בשבעת הימים הקרובים."),
    ("פריצה טכנית", "מידע", "המחיר עבר את השיאים האחרונים בנפח גבוה. מידע בלבד: פריצה לא נכנסת להערכת ההשקעה."),
    ("רוטציית סקטורים", "מידע", "הענף החזק ביותר (ציון 70 ומעלה) והחלש ביותר (ציון מתחת ל-35), לפי תעודות סל ענפיות. אומדן, לא מדידה של תנועות כסף."),
)


def _when(ed: str, today) -> str:
    try:
        d = datetime.strptime(str(ed)[:10], "%Y-%m-%d").date()
    except ValueError:
        return ""
    n = (d - today).days
    dm = d.strftime("%d/%m/%Y")
    return f"היום, {dm}" if n == 0 else f"מחר, {dm}" if n == 1 else f"ב-{dm}"


def _down_day(row) -> str:
    c = _n((row or {}).get("DailyChange%"))
    if c is None or abs(c) < 3:
        return ""
    return f" המניה {'עלתה' if c > 0 else 'ירדה'} {abs(c):.2f}% ביום המסחר האחרון."


def item(a: dict, rows: dict, vmap: dict, events: dict, mkt: dict, close: str, today) -> dict:
    kind, scope = a.get("type") or "", a.get("scope") or ""
    row, v = rows.get(scope) or {}, vmap.get(scope) or {}
    name = H.short_name(row.get("Name"), scope) if row else scope
    ev = (events or {}).get(scope) or {}
    title, text, link = a.get("message") or kind, "", "company"
    if kind == "אזהרת סיכון":
        title = f"{name}: סיכון גבוה ומגמת ירידה"
        text = "המחיר מתחת לממוצע של 200 יום, ורמת הסיכון של המניה גבוהה." + _down_day(row)
    elif kind == "שינוי דירוג":
        act, firm = ev.get("rating_action"), ev.get("rating_firm")
        title = f"{name}: {act}" if act else title
        text = ((f"בית ההשקעות {firm} שינה את ההמלצה שלו. " if firm else "")
                + "זו דעה של גורם חיצוני, והיא לא משנה את הערכת ההשקעה של המערכת.")
    elif kind == "זינוק נפח":
        vr = _n(row.get("VolRatio"))
        title = f"{name}: נפח מסחר פי {vr:.2f} מהממוצע" if vr else f"{name}: נפח מסחר חריג"
        text = "הרבה יותר מניות החליפו ידיים מהרגיל. זה מראה עניין חריג, לא את הכיוון." + _down_day(row)
    elif kind == "דוחות":
        when = _when(ev.get("earnings_date"), today)
        title = f"{name} מפרסמת דוחות {when}".strip()
        text = "ביום דוחות המחיר יכול לזוז בחדות, לשני הכיוונים." + _down_day(row)
    elif kind == "פריצה טכנית":
        title = f"{name}: פריצה טכנית בנפח גבוה"
        text = "המחיר עבר את השיאים האחרונים. מידע בלבד, לא המלצת קנייה: פריצה לא נכנסת להערכת ההשקעה."
    elif kind == "רוטציית סקטורים":
        sec = next((s for s in (mkt or {}).get("sectors") or [] if s.get("sector") == scope), {})
        rs = _n(sec.get("rs"))
        strong = (_n(sec.get("score")) or 0) >= 50
        title = f"{'חוזק' if strong else 'חולשה'} בענף {scope}"
        rel = "" if rs is None else (f"חוזק יחסי של {rs:.1f}% מעל S&P 500 בחודש האחרון. " if rs >= 0
                                     else f"חוזק יחסי של {abs(rs):.1f}% מתחת ל-S&P 500 בחודש האחרון. ")
        text = rel + "אומדן של המערכת מתעודת הסל של הענף, לא מדידה של תנועות כסף."
        link, name = "markets", scope
    grp = SEVERITY.get(a.get("severity"), "info")
    tag = ({"label": v.get("label"), "tone": v.get("tone")} if v and link == "company" else None)
    return {"group": grp, "kind": kind, "ticker": scope if link == "company" else "", "name": name,
            "title": title, "text": text, "tag": tag, "link": link, "date": close, "raw": a.get("message") or ""}


def build(alerts: list, rows: dict, vmap: dict, events: dict, mkt: dict, close: str, today) -> dict:
    items = [item(a, rows, vmap, events, mkt, close, today) for a in alerts or []]
    counts = {g: sum(1 for i in items if i["group"] == g) for g, *_ in GROUPS}
    return {"items": items, "counts": counts, "total": len(items)}
