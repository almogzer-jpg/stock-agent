# -*- coding: utf-8 -*-
"""Glossary screen data. The terms come from glossary.py (one home for every term in
the app), grouped by first letter and filtered by a search. Where the day's data has
the number, a term gets a real example from one stock: the first pick on the home
screen. A term with no reliable number gets no example rather than an invented one."""
from dashboard.v4 import home_data as H
from dashboard.v4.company_data import big_money, pct1

import glossary as G

LATIN = "A–Z"


def _n(v):
    return v if isinstance(v, (int, float)) and v == v else None


def _to(name: str) -> str:
    """The Hebrew prefix ל before a name: "ל-Chevron", "לאפל"."""
    return f"ל{name}" if name[:1] and "א" <= name[:1] <= "ת" else f"ל-{name}"


def letter(term: str) -> str:
    c = term[:1]
    return c if "א" <= c <= "ת" else LATIN


def entries() -> list:
    return [{"term": t, **e} for t, e in G.TERMS.items()]


def matches(e: dict, q: str) -> bool:
    q = (q or "").strip().lower()
    if not q:
        return True
    return any(q in h.lower() for h in (e["term"], *e.get("aliases", []), e["short"]))


def sample(rows: dict, vmap: dict):
    """The stock the examples are taken from: the home screen's first pick."""
    import stockdata
    buys = stockdata.ranked(vmap, rows, "buy", limit=1) or stockdata.ranked(vmap, rows, limit=1)
    if not buys:
        return None
    t = buys[0]["ticker"]
    return {"ticker": t, "row": rows.get(t, {}), "v": buys[0], "name": H.short_name(rows.get(t, {}).get("Name"), t)}


# ------------------------------------------------------------------ examples
def _target(r, name):
    tm, p, n = _n(r.get("TargetMean")), _n(r.get("Price")), _n(r.get("AnalystCount"))
    if tm is None or p is None:
        return None
    who = f" לפי {int(n)} אנליסטים" if n else ""
    tail = ("כלומר המחיר כבר מעל היעד." if p > tm else f"כלומר היעד גבוה ב-{(tm / p - 1) * 100:.1f}% מהמחיר.")
    return f"{_to(name)} יעד ממוצע של {H.money(tm)}{who}, והמחיר {H.money(p)}. {tail}"


def _upside(r, name):
    tm, p = _n(r.get("TargetMean")), _n(r.get("Price"))
    if tm is None or p is None:
        return None
    up = (tm / p - 1) * 100
    if up <= 0:
        return f"היעד הממוצע של {name} נמוך מהמחיר ב-{abs(up):.1f}%, ולכן לפי היעד אין פוטנציאל עלייה."
    return f"לפי היעד הממוצע, הפוטנציאל של {name} הוא {pct1(up)}."


def _support(r, name):
    s, d = _n(r.get("Support")), _n(r.get("DistSupport%"))
    if s is None:
        return None
    return f"התמיכה של {name} ב-{H.money(s)}" + (f", כ-{abs(d):.0f}% מתחת למחיר." if d is not None else ".")


def _resistance(r, name):
    if _n(r.get("Price")) is None:
        return None
    res, d = _n(r.get("Resistance")), _n(r.get("DistResistance%"))
    if res is None:
        return f"{_to(name)} לא זוהתה התנגדות מעל המחיר, כי המחיר מעל כל הרמות שזוהו."
    return f"ההתנגדות של {name} ב-{H.money(res)}" + (f", כ-{d:.0f}% מעל המחיר." if d is not None else ".")


def _rr(r, name):
    if _n(r.get("Price")) is None:
        return None
    rr = _n(r.get("RiskReward"))
    if rr is None:
        return f"{_to(name)} אין היום יחס טכני, כי לא זוהתה התנגדות מעל המחיר או תמיכה מתחתיו."
    return f"היחס הטכני של {name} הוא {rr:.2f}."


def _ma(r, name):
    ma, p = _n(r.get("MA200")), _n(r.get("Price"))
    if ma is None or p is None:
        return None
    return f"הממוצע ל-200 יום של {name} הוא {H.money(ma)}, והמחיר {H.money(p)}, {'מעליו' if p >= ma else 'מתחתיו'}."


def _growth(r, name):
    g = _n(r.get("RevenueGrowth"))
    if g is None:
        return None
    return f"ברבעון האחרון המכירות של {name} {'גדלו' if g >= 0 else 'ירדו'} ב-{abs(g):.1f}% לעומת הרבעון המקביל אשתקד."


def _report(r, name):
    if r.get("LastReport"):
        return f"{name} פרסמה את הדוח האחרון ב-{r['LastReport']}."
    if r.get("LastQuarter"):
        return f"הנתונים העסקיים של {name} מתארים את הרבעון שהסתיים ב-{r['LastQuarter']}."
    return None


def _simple(field, fmt):
    def f(r, name):
        v = _n(r.get(field))
        return fmt(v, name) if v is not None else None
    return f


EXAMPLES = {
    "סימול": lambda r, name: f"{name} נסחרת בסימול {r['Ticker']}." if r.get("Ticker") else None,
    "שווי שוק": _simple("MarketCap", lambda v, n: f"שווי השוק של {n} הוא {big_money(v)}."),
    "סקטור": lambda r, name: f"{name} פועלת בענף {H.sector_he(r)}." if r.get("Sector") else None,
    "דוחות רבעוניים": _report,
    "מחיר יעד": _target,
    "פוטנציאל עלייה": _upside,
    "תמיכה": _support,
    "התנגדות": _resistance,
    "יחס סיכוי/סיכון": _rr,
    "ממוצע נע": _ma,
    "RSI": _simple("RSI14", lambda v, n: f"ה-RSI של {n} הוא {v:.1f}."),
    "מומנטום": _simple("Ret3m", lambda v, n: f"{n} {'עלתה' if v >= 0 else 'ירדה'} {abs(v):.1f}% בשלושה חודשים."),
    "נפח מסחר": _simple("VolRatio", lambda v, n: f"ביום המסחר האחרון נסחרו במניית {n} פי {v:.1f} מהממוצע של 20 הימים האחרונים."),
    "תנודתיות": _simple("Volatility", lambda v, n: f"התנודתיות של {n} היא {v:.1f}% בחישוב שנתי."),
    "ביתא": _simple("Beta", lambda v, n: f"הביתא של {n} היא {v:.2f}, " + (
        "כלומר בתקופת המדידה היא נטתה לנוע בכיוון הפוך לשוק." if v < 0 else
        f"כלומר היא {'פחות' if v < 1 else 'יותר'} רגישה לתנועות השוק.")),
    "ירידה מקסימלית": _simple("MaxDrawdown", lambda v, n: f"הירידה הגדולה ביותר של {n} בשנה האחרונה: {pct1(v)}."),
    "רמת סיכון": lambda r, name: f"רמת הסיכון של {name}: {r['RiskLevel']}." if r.get("RiskLevel") else None,
    "מכפיל עתידי": _simple("ForwardPE", lambda v, n: f"המכפיל העתידי של {n} הוא {v:.1f}."),
    "PEG": _simple("PEG", lambda v, n: f"ה-PEG של {n} הוא {v:.2f}."),
    "צמיחת הכנסות": _growth,
    "שולי רווח": _simple("OperatingMargin", lambda v, n: f"הרווח התפעולי של {n} הוא {v:.1f}% מהמכירות."),
    "ROIC": _simple("ROIC", lambda v, n: f"התשואה על ההון המושקע של {n} היא {v:.1f}%."),
    "חוב/הון": _simple("DebtToEquity", lambda v, n: f"יחס החוב להון של {n} הוא {v:.2f}."),
}


def example(term: str, s: dict | None):
    if not s or term not in ("ציון איכות", "אמינות הנתונים", "הערכת השקעה", *EXAMPLES):
        return None
    v, name = s["v"], s["name"]
    if term == "ציון איכות":
        return f"ציון האיכות של {name} הוא {v['quality']:.0f} מתוך 100." if _n(v.get("quality")) is not None else None
    if term == "אמינות הנתונים":
        sc = _n((v.get("reliability") or {}).get("score"))
        return f"אמינות הנתונים של {name} היא {sc:.0f} מתוך 100." if sc is not None else None
    if term == "הערכת השקעה":
        return f"הערכת ההשקעה של {name} היום: {v['label']}."
    return EXAMPLES[term](s["row"], name)


def build(q: str, s: dict | None) -> dict:
    """Sections by first letter (Hebrew order, Latin terms last), each term with its example."""
    items = [{**e, "letter": letter(e["term"]), "example": example(e["term"], s)}
             for e in entries() if matches(e, q)]
    items.sort(key=lambda e: (e["letter"] == LATIN, e["term"].lower()))
    sections = []
    for e in items:
        if not sections or sections[-1]["letter"] != e["letter"]:
            sections.append({"letter": e["letter"], "items": []})
        sections[-1]["items"].append(e)
    present = {x["letter"] for x in sections}
    return {"sections": sections, "count": len(items), "total": len(G.TERMS),
            "with_example": sum(1 for e in items if e["example"]),
            "letters": [(c, c in present) for c in "אבגדהוזחטיכלמנסעפצקרשת"] + [(LATIN, LATIN in present)]}
