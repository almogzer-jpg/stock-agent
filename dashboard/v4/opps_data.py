# -*- coding: utf-8 -*-
"""Opportunities screen view model (V4). Pure functions, no Streamlit, so they are tested.

Every row is the LIVE engine's verdict (stockdata.ranked), in the live order, so a
stock reads the same here, on the home screen and in the company analysis.
"""
from dashboard.v4 import home_data as H

ACTIONS = ("buy", "wait", "avoid")
TAB_LABEL = {"buy": "שווה לשקול קנייה", "wait": "להמתין להזדמנות", "avoid": "לא עכשיו"}   # the full wording, never shortened
RISKS = ("נמוך", "בינוני", "גבוה", "גבוה מאוד")
SORTS = {"quality": "איכות החברה", "change": "שינוי יומי", "name": "שם החברה", "reliability": "אמינות הנתונים"}
ALL = "הכול"
PAGE = 10


def coverage(rows: dict, vmap: dict) -> dict:
    """How many stocks have a verdict at all. Only stocks that went through the full
    business analysis get one: the daily scan picks them by technical momentum, plus
    the system's fixed watchlist. Shown, not hidden (owner request 01/11/2026)."""
    n = {a: 0 for a in ("buy", "wait", "avoid", "nodata")}
    for v in vmap.values():
        n[v["action"]] = n.get(v["action"], 0) + 1
    rated = sum(1 for t in vmap if rows.get(t, {}).get("_tier") in ("full", "enriched"))
    return {**n, "all": len(vmap), "rated": rated, "unrated": len(vmap) - rated}


def coverage_text(cov: dict, advanced: bool = False) -> str:
    text = (f"הערכת השקעה ניתנת רק למניות שעברו ניתוח עסקי מלא: {cov['rated']} מתוך {cov['all']}. "
            "הסריקה היומית בוחרת אותן לפי תנועת המחיר האחרונה (המומנטום), יחד עם רשימת המעקב הקבועה של המערכת. "
            f"ל-{cov['unrated']} המניות האחרות אין עדיין הערכת השקעה, ולכן חברה טובה במגמה חלשה לא תופיע כאן.")
    if advanced:
        text += " כלומר הרשימה מוטה מראש לטובת מניות במומנטום, וכדאי לקרוא אותה כך."
    return text


def _row(v: dict, r: dict) -> dict:
    t = v["ticker"]
    name = H.short_name(r.get("Name"), t)
    return {
        "ticker": t, "name": name, "ini": (name or t)[:1].upper(), "sector": H.sector_he(r),
        "price": H.money(r.get("Price")), "chg": H.pct(r.get("DailyChange%")), "chg_tone": H.tone_of(r.get("DailyChange%")),
        "chg_n": H._n(r.get("DailyChange%")),
        "label": v["label"], "tone": v["tone"], "why": v.get("why") or "",
        "dims": H.card_dims(v, r), "risk": r.get("RiskLevel"),
        "quality": v.get("quality"), "reliability": (v.get("reliability") or {}).get("score"),
        "stale": H.stale_note(r),
    }


def table(rows: dict, vmap: dict, action: str = "buy", sector: str = ALL, risk: str = ALL, sort: str = "quality") -> dict:
    """The rows of one tab after filters, plus the filter options that tab offers."""
    import stockdata
    items = [_row(v, rows.get(v["ticker"], {})) for v in stockdata.ranked(vmap, rows, action)]
    sectors = H._count([x["sector"] for x in items])
    risks = [k for k in RISKS if any(x["risk"] == k for x in items)]
    sector = sector if sector == ALL or sector in dict(sectors) else ALL
    risk = risk if risk == ALL or risk in risks else ALL
    out = [x for x in items if (sector == ALL or x["sector"] == sector) and (risk == ALL or x["risk"] == risk)]
    if sort == "change":
        out.sort(key=lambda x: -(x["chg_n"] if x["chg_n"] is not None else -1e9))
    elif sort == "name":
        out.sort(key=lambda x: (x["name"] or x["ticker"]).lower())
    elif sort == "reliability":
        out.sort(key=lambda x: -(x["reliability"] or 0))
    return {"rows": out, "total": len(items), "sector": sector, "risk": risk, "sort": sort if sort in SORTS else "quality",
            "sectors": [{"name": s, "n": n} for s, n in sectors], "risks": risks}


def mix(rows_: list) -> list:
    """Sector mix of a list of table rows, for the transparency panel."""
    m = H._count([x["sector"] for x in rows_])
    top = m[0][1] if m else 1
    return [{"name": s, "n": n, "w": f"{max(4, n / top * 100):.0f}%"} for s, n in m]
