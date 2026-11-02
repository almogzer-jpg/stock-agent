# -*- coding: utf-8 -*-
"""Home screen view model (V4). Pure functions, no Streamlit, so they are tested.

Owner rule (01/11/2026): every recommendation shown comes from the LIVE engine
(verdict.py via stockdata), never from the four-dimension shadow engine. The
four small answers on each card are the live verdict's own facets (quality,
price), its trend and the row's risk level, the same words other screens use.
"""
from datetime import date, datetime

DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]
DEFENSIVE = {"שירותים ציבוריים", "צריכה בסיסית", "בריאות"}
TECH_SECTORS = {"טכנולוגיה", "שירותי תקשורת"}
COUNT_HE = {2: "שתי", 3: "שלוש", 4: "ארבע", 5: "חמש"}


def _n(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def pct(x, digits=2):
    x = _n(x)
    if x is None:
        return "—"
    return ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x):.{digits}f}%"


def tone_of(x, invert=False):
    x = _n(x)
    if x is None or x == 0:
        return "muted"
    good = x > 0 if not invert else x < 0
    return "positive" if good else "negative"


SUFFIXES = (" Holdings Corporation", " Corporation", " Incorporated", ", Inc.", " Inc.", " Inc", " Corp.", " Corp",
            " Company", " Co.", " plc", " PLC", " Ltd.", " N.V.", " S.A.", " Holdings")
TRUNCATED_WORDS = ("Incorporated", "Corporation", "Holdings", "Company", "International")


def short_name(name, ticker=None):
    """Display name without the corporate suffix ("Apple Inc." -> "Apple")."""
    n = (name or ticker or "").strip()
    head, _, last = n.rpartition(" ")              # the data source cuts long names ("... Incorpor")
    if head and len(last) >= 3 and any(w.startswith(last) and w != last for w in TRUNCATED_WORDS):
        n = head
    changed = True
    while changed:
        changed = False
        for s in SUFFIXES:
            if n.endswith(s) and len(n) > len(s) + 1:
                n, changed = n[: -len(s)].rstrip(" ,"), True
    for tail in (" and", " &"):
        if n.endswith(tail):
            n = n[: -len(tail)]
    return n


def sector_he(row: dict) -> str:
    from market import SECTOR_EN_TO_HE
    s = (row or {}).get("Sector")
    return SECTOR_EN_TO_HE.get(s) or s or "ענף לא ידוע"


STALE_DAYS = 1                       # any business data older than the close it is shown with


def fund_age(row: dict) -> int | None:
    """Days between the business data behind a verdict and the close it is shown with."""
    try:
        f = datetime.strptime(str((row or {}).get("FundDate"))[:10], "%d/%m/%Y").date()
        c = datetime.strptime(str((row or {}).get("Date"))[:10], "%d/%m/%Y").date()
    except ValueError:
        return None
    return (c - f).days


def _d(s):
    try:
        return datetime.strptime(str(s)[:10], "%d/%m/%Y").date()
    except ValueError:
        return None


REPORT_LAG_DAYS = 95      # a report covers a quarter that ended at most about three months earlier


def stale_note(row: dict) -> str:
    """A short warning when the assessment rests on business data that predates the
    latest published report, or is older than the close. Empty when the data is current
    or its dates are unknown. Three dates are kept apart: the period the figures
    describe (LastQuarter), when they were fetched (FundDate) and the close (Date)."""
    row = row or {}
    q, rep, f = _d(row.get("LastQuarter")), _d(row.get("LastReport")), _d(row.get("FundDate"))
    if rep and q and (rep - q).days > REPORT_LAG_DAYS:
        return (f"דוח כספי חדש פורסם ב-{row['LastReport']}, אבל הנתונים העסקיים שעליהם נשענת ההערכה "
                f"עדיין של הרבעון שהסתיים ב-{row['LastQuarter']}.")
    if rep and f and f < rep:
        return (f"דוח כספי חדש פורסם ב-{row['LastReport']}, וההערכה נשענת על נתונים עסקיים "
                f"שנשלפו לפניו ({row['FundDate']}).")
    age = fund_age(row)
    if age is None or age < STALE_DAYS:
        return ""
    days = "יום אחד" if age == 1 else f"{age} ימים"
    return f"ההערכה נשענת על נתונים עסקיים מ-{row['FundDate']}, {days} לפני הסגירה. ייתכן שדוח חדש עוד לא נכלל."


def money(v):
    v = _n(v)
    if v is None:
        return "—"
    return f"${v:,.2f}"


def day_label(d: date):
    return DAYS_HE[d.weekday()], d.strftime("%d/%m")


# ------------------------------------------------------------------ market
def market_state(regime: dict | None):
    """The three-step market state from the regime score (same thresholds as market.py)."""
    s = _n((regime or {}).get("score"))
    if s is None:
        return "unknown", "לא ידוע"
    if s >= 70:
        return "positive", "חיובי"
    if s >= 40:
        return "neutral", "ניטרלי"
    return "negative", "שלילי"


def _join_he(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " ו" + items[-1]


def market_story(g: dict, mkt: dict) -> dict:
    """Headline, one explanatory paragraph and three figures for the market card.
    Built only from validated data: if the global markets file did not pass
    globalmkt.check, the figures are hidden and the card says why."""
    key, label = market_state(mkt.get("regime"))
    by = {r.get("symbol"): r for r in (g.get("strip") or [])}
    ok = g.get("status") == "ok"
    spx, nas, vix = (by.get(s, {}) for s in ("^GSPC", "^IXIC", "^VIX"))
    s1, n1, v1 = _n(spx.get("d1")), _n(nas.get("d1")), _n(vix.get("d1"))
    sectors = sorted(mkt.get("sectors") or [], key=lambda s: -(_n(s.get("score")) or 0))

    if ok and s1 is not None:
        if s1 <= -1:
            head = "יום של ירידות"
        elif s1 >= 1:
            head = "יום של עליות"
        elif s1 < -0.3:
            head = "ירידות קלות בשוק"
        elif s1 > 0.3:
            head = "עליות קלות בשוק"
        else:
            head = "יום שקט יחסית בשוק"
        if n1 is not None and (n1 < 0) == (s1 < 0) and abs(n1) - abs(s1) >= 0.5 and abs(s1) > 0.3:
            head += ", בעיקר בטכנולוגיה"
        head += "."
        day = {s.get("sector"): _n(s.get("change_pct")) for s in sectors}
        held = [n for n in DEFENSIVE if (day.get(n) is not None and day[n] >= 0)]
        if s1 <= -0.5 and len(held) >= 2:
            head += " הענפים הדפנסיביים החזיקו מעמד."
    else:
        head = {"positive": "השוק במגמה חיובית.", "neutral": "השוק במצב מעורב.",
                "negative": "השוק במגמה שלילית.", "unknown": "מצב השוק לא ידוע כרגע."}[key]

    parts = []
    if ok and v1 is not None and _n(vix.get("price")) is not None:
        vp = _n(vix["price"])
        if v1 >= 5:
            parts.append(f"מדד הפחד (VIX) עלה ל-{vp:.1f}: המשקיעים מצפים לתנודות גדולות יותר בימים הקרובים.")
        elif v1 <= -5:
            parts.append(f"מדד הפחד (VIX) ירד ל-{vp:.1f}: השוק רגוע יותר.")
        else:
            parts.append(f"מדד הפחד (VIX) יציב, סביב {vp:.1f}.")
    strong = [s["sector"] for s in sectors if (_n(s.get("score")) or 0) >= 60][:3]
    weak = [s["sector"] for s in reversed(sectors) if (_n(s.get("score")) or 100) < 40][:2]
    if strong:
        parts.append(f"הענפים החזקים כרגע: {_join_he(strong)}." + (f" החלשים: {_join_he(weak)}." if weak else ""))

    figs = []
    if ok:
        for sym, name, invert in (("^GSPC", "S&P 500", False), ("^IXIC", "נאסד״ק", False), ("^VIX", "מדד הפחד (VIX)", True)):
            r = by.get(sym) or {}
            p = _n(r.get("price"))
            figs.append({"name": name, "val": "דורש אימות" if p is None and r.get("suspect") else
                         ("—" if p is None else (f"{p:,.1f}" if sym == "^VIX" else f"{p:,.0f}")),
                         "chg": pct(r.get("d1")) if r.get("d1") is not None else "",
                         "tone": tone_of(r.get("d1"), invert=invert)})
    return {"state": key, "label": label, "headline": head, "body": " ".join(parts), "figures": figs,
            "status": g.get("status", "missing"), "message": g.get("message", ""), "updated": g.get("updated")}


# ------------------------------------------------------------------ picks
TREND = {"up": ("חיובית", "positive"), "mixed": ("מעורבת", "warning"), "down": ("שלילית", "negative"),
         "unknown": ("אין נתון", "muted")}
RISK = {"נמוך": "positive", "בינוני": "warning", "גבוה": "negative", "גבוה מאוד": "negative"}


def _strip(label, prefix):
    return label[len(prefix):].strip() if isinstance(label, str) and label.startswith(prefix) else (label or "אין נתון")


def card_dims(v: dict, row: dict) -> list:
    """The four small answers on a card, from the live verdict only."""
    f = v.get("facets") or {}
    q, p = f.get("quality") or {}, f.get("price") or {}
    tw, tt = TREND.get(v.get("trend") or "unknown", TREND["unknown"])
    rl = row.get("RiskLevel")
    # Company, trend and risk decide. Price is supplementary, so it comes last and says so.
    return [
        {"k": "חברה", "v": _strip(q.get("label"), "חברה "), "tone": q.get("tone") or "muted"},
        {"k": "מגמה", "v": tw, "tone": tt},
        {"k": "סיכון", "v": rl or "אין נתון", "tone": RISK.get(rl, "muted")},
        {"k": "מחיר (משלים)", "v": _strip(p.get("label"), "מחיר "), "tone": p.get("tone") or "muted"},
    ]


def picks(rows: dict, vmap: dict, limit: int = 3) -> dict:
    """The live engine's best 'buy' verdicts (same order as every other screen)."""
    import stockdata
    buys = stockdata.ranked(vmap, rows, "buy")
    cards = []
    for v in buys[:limit]:
        t = v["ticker"]
        r = rows.get(t, {})
        name = short_name(r.get("Name"), t)
        cards.append({
            "ticker": t, "name": name, "ini": (name or t)[:1].upper(), "sector": sector_he(r),
            "price": money(r.get("Price")), "chg": pct(r.get("DailyChange%")), "chg_tone": tone_of(r.get("DailyChange%")),
            "label": v["label"], "tone": v["tone"], "why": v.get("why") or "",
            "dims": card_dims(v, r),
            "quality": v.get("quality"), "reliability": (v.get("reliability") or {}).get("score"),
            "stale": stale_note(r),
            "calm": calm(card_dims(v, r), r, stale_note(r)),
        })
    return {"cards": cards, "total": len(buys), "next_quality": buys[limit]["quality"] if len(buys) > limit else None,
            "sectors": _count([sector_he(rows.get(v["ticker"], {})) for v in buys])}


DATA_OLD_DAYS = 3       # Friday's close on a Monday is current. Thursday's on a Monday is not.


def data_warning(close: str, today: date, sync: dict | None = None) -> str:
    """The banner text when the screens may show old data, or "" when they do not."""
    d = _d(close)
    if sync is not None and (not sync.get("files") or {"results.csv", "universe.json"} & {
            f.split(":")[0] for f in sync.get("failed", [])}):
        when = f" מ-{close}" if d else ""
        return (f"לא הצלחנו לעדכן את הנתונים מהמערכת. מוצגים הנתונים האחרונים שנשמרו{when}, "
                "וייתכן שאינם עדכניים. נסו לרענן בעוד כמה דקות.")
    if d and (today - d).days > DATA_OLD_DAYS:
        return (f"הנתונים לפי סגירת המסחר של {close}, לפני {(today - d).days} ימים. ייתכן שיש נתוני מסחר חדשים יותר "
                "שעוד לא נטענו. העדכון האוטומטי רץ בימי חול בסביבות הצהריים.")
    return ""


def calm(dims: list, r: dict, stale: str) -> bool:
    """A card can be shown compact only when nothing on it needs attention: all four
    answers positive, the data current, and the price not above the analysts' target."""
    p, tm = _n(r.get("Price")), _n(r.get("TargetMean"))
    return (bool(dims) and all(d["tone"] == "positive" for d in dims) and not stale
            and not (p is not None and tm is not None and p > tm))


def _count(items) -> list:
    """[(item, n)] most common first, ties in first-seen order."""
    seen = {}
    for x in items:
        seen[x] = seen.get(x, 0) + 1
    return sorted(seen.items(), key=lambda kv: -kv[1])


def concentration(pk: dict) -> dict | None:
    """Owner request 01/11/2026: never force sector diversity on the picks, but say
    plainly when the shown picks share a sector, why, and how wide the full list is."""
    cards = pk.get("cards") or []
    if len(cards) < 2:
        return None
    top, k = _count([c["sector"] for c in cards])[0]
    if k < 2:
        return None
    n, total, mix = len(cards), pk.get("total") or 0, pk.get("sectors") or []
    in_sector = dict(mix).get(top, k)
    who = f"כל {COUNT_HE.get(n, n)} המניות כאן" if k == n else f"{COUNT_HE.get(k, k)} מתוך {COUNT_HE.get(n, n)} המניות כאן"
    text = (f"{who} מאותו ענף: {top}. הן מוצגות כי קיבלו היום את ציון האיכות הגבוה ביותר, לא בגלל בחירה לפי ענף. "
            f"בכל {total} המניות שקיבלו את ההערכה הזו יש {len(mix)} ענפים, ו-{in_sector} מהן מענף {top}.")
    qs = [c["quality"] for c in cards if c.get("quality") is not None]
    detail = ""
    if qs:
        detail = f"ציוני האיכות כאן: {' · '.join(f'{q:.0f}' for q in qs)}"
        if pk.get("next_quality") is not None:
            detail += f", והבאה בתור: {pk['next_quality']:.0f}"
        detail += ". "
    detail += "ציון האיכות כולל 20% חוזק ענף ו-25% מצב טכני, ולכן ענף במומנטום מקבל דחיפה לכל המניות שבו."
    return {"sector": top, "k": k, "n": n, "text": text, "detail": detail.strip(),
            "mix": [{"name": s, "n": c} for s, c in mix]}


# ------------------------------------------------------------------ this week
def week(events: dict, rows: dict, g: dict, today: date, limit: int = 3) -> list:
    """What matters this week: earnings in the next 7 days (the user's stocks first),
    then a sharp move in market volatility. Real dates only."""
    out = []
    for t, e in (events or {}).items():
        d = (e or {}).get("earnings_date")
        try:
            dd = datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if 0 <= (dd - today).days <= 7:
            name = short_name((rows.get(t) or {}).get("Name"), t)
            day, dm = day_label(dd)
            out.append({"sort": (1, dd), "day": day, "date": dm,
                        "title": f"{name} מפרסמת דוחות",
                        "text": "ביום דוחות המחיר יכול לזוז בחדות."})
    out.sort(key=lambda x: x["sort"])
    vix = next((r for r in (g.get("strip") or []) if r.get("symbol") == "^VIX"), None)
    if g.get("status") == "ok" and vix and _n(vix.get("d1")) is not None and abs(vix["d1"]) >= 10:
        try:
            dd = datetime.strptime(vix.get("as_of", ""), "%d/%m/%Y").date()
            day, dm = day_label(dd)
        except ValueError:
            day, dm = "", ""
        up = vix["d1"] > 0
        out.append({"sort": (2, today), "day": day, "date": dm, "title": "התנודתיות עלתה" if up else "התנודתיות ירדה",
                    "text": f"מדד הפחד {'קפץ' if up else 'ירד'} ב-{abs(vix['d1']):.0f}%." + (" ימים חדים יותר צפויים." if up else "")})
    return [{k: v for k, v in x.items() if k != "sort"} for x in out[:limit]]


# ------------------------------------------------------------------ advanced
def market_table(g: dict) -> list:
    rows = []
    if g.get("status") != "ok":
        return rows
    for r in g.get("strip") or []:
        p = _n(r.get("price"))
        rows.append({"name": r.get("name"), "val": ("דורש אימות" if r.get("suspect") else "—") if p is None else f"{p:,.2f}",
                     "d1": pct(r.get("d1")), "d1_tone": tone_of(r.get("d1"), invert=r.get("symbol") == "^VIX"),
                     "d30": pct(r.get("d30")), "trend": r.get("trend") or "—"})
    return rows


def sector_bars(mkt: dict) -> list:
    out = []
    for s in sorted(mkt.get("sectors") or [], key=lambda s: -(_n(s.get("score")) or 0)):
        sc = _n(s.get("score"))
        if sc is None:
            continue
        out.append({"name": s.get("sector"), "score": int(sc), "w": f"{max(3, sc):.0f}%",
                    "tone": "positive" if sc >= 60 else "warning" if sc >= 40 else "negative"})
    return out


def footer(rel: dict, g: dict, close: str) -> dict:
    r = (rel or {}).get("reliability") or {}
    return {"rel_label": r.get("label") or "לא ידוע", "rel_score": r.get("score"),
            "market_updated": (g.get("updated") or "—") if g.get("status") == "ok" else "לא אומת",
            "close": close or "—"}
