# -*- coding: utf-8 -*-
"""Markets screen view model (V4). Pure functions, no Streamlit, so they are tested.

Global market values are read only through globalmkt.check: a value that failed
validation arrives hidden (price None, suspect True) and is shown as "דורש אימות"
or "אין נתון", never as a number. The market score, fear and greed, sector
strength and breadth are the system's own calculations (market_overview.json),
shown with their date and labelled as calculations.
"""
from datetime import date, datetime

import config
from dashboard.v4 import home_data as H

_n = H._n

NAMES = {"^GSPC": "S&P 500", "^IXIC": "נאסד״ק", "^DJI": "דאו ג׳ונס", "^RUT": "ראסל 2000",
         "^GDAXI": "DAX · גרמניה", "^N225": "ניקיי · יפן", "^FTSE": "FTSE · בריטניה", "^HSI": "הנג סנג · הונג קונג",
         "^TNX": "תשואת אג״ח 10 שנים", "2YY=F": "תשואת אג״ח שנתיים", "DX-Y.NYB": "מדד הדולר",
         "ILS=X": "דולר/שקל", "EURILS=X": "אירו/שקל", "GBPILS=X": "ליש״ט/שקל", "EURUSD=X": "אירו/דולר",
         "CL=F": "נפט WTI", "BZ=F": "נפט ברנט", "GC=F": "זהב", "SI=F": "כסף", "NG=F": "גז טבעי",
         "BTC-USD": "ביטקוין", "ETH-USD": "את׳ריום", "SOL-USD": "סולאנה", "XRP-USD": "XRP"}
US = ("^GSPC", "^IXIC", "^DJI", "^RUT")
YIELDS = ("^TNX", "2YY=F")
DOLLAR = ("CL=F", "BZ=F", "GC=F", "SI=F", "NG=F", "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD")
SECTIONS = (  # (key, title, symbols in simple mode, extra symbols in advanced mode)
    ("equity", "מדדי מניות", ("^GSPC", "^IXIC", "^DJI", "^RUT", "^GDAXI", "^N225"), ("^FTSE", "^HSI")),
    ("rates", "ריבית ומטבעות", ("^TNX", "2YY=F", "ILS=X", "EURILS=X", "DX-Y.NYB"), ("GBPILS=X", "EURUSD=X")),
    ("commodity", "סחורות", ("CL=F", "BZ=F", "GC=F", "SI=F", "NG=F"), ()),
    ("crypto", "קריפטו", ("BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"), ()),
)
STALE_DAYS = 4


def _by_symbol(g: dict) -> dict:
    return {r.get("symbol"): r for rows in (g.get("groups") or {}).values() for r in rows or [] if r.get("symbol")}


def _val(sym, p):
    if sym in YIELDS:
        return f"{p:.2f}%"
    if sym in DOLLAR:
        return f"${p:,.2f}"
    if sym.endswith("=X"):
        return f"{p:.3f}"
    return f"{p:,.2f}"


def _bp(price, d1):
    """Daily change of a yield in basis points (hundredths of a percentage point)."""
    if price is None or d1 is None or d1 <= -100:
        return None
    prev = price / (1 + d1 / 100)
    return round((price - prev) * 100)


def row(r: dict) -> dict:
    """One asset as shown: value, today's change, the trend word, and its status."""
    sym = r.get("symbol")
    p, d1 = _n(r.get("price")), _n(r.get("d1"))
    name = NAMES.get(sym) or r.get("name") or sym
    if r.get("suspect"):
        return {"sym": sym, "name": name, "status": "verify", "val": "דורש אימות", "d1": "", "d1_tone": "muted",
                "d7": "", "d30": "", "trend": "", "why": r.get("suspect_reason") or "", "as_of": r.get("as_of") or "—"}
    if p is None:
        return {"sym": sym, "name": name, "status": "missing", "val": "אין נתון", "d1": "", "d1_tone": "muted",
                "d7": "", "d30": "", "trend": "", "why": "המקור לא החזיר ערך", "as_of": "—"}
    if sym in YIELDS:
        bp = _bp(p, d1)
        chg = "—" if bp is None else f"{'+' if bp > 0 else '−' if bp < 0 else ''}{abs(bp)} נ״ב"
    else:
        chg = H.pct(d1)
    trend = (r.get("trend") or "").replace("↑", "").replace("↓", "").replace("→", "").strip()
    return {"sym": sym, "name": name, "status": "ok", "val": _val(sym, p), "d1": chg,
            "d1_tone": H.tone_of(d1, invert=sym in YIELDS or sym == "^VIX"),
            "d7": H.pct(r.get("d7")), "d30": H.pct(r.get("d30")), "trend": "" if trend == "—" else trend,
            "trend_tone": ("muted" if sym in YIELDS or sym == "^VIX" else
                           "positive" if "עול" in trend else "negative" if "יורד" in trend else "muted"),
            "why": "", "as_of": r.get("as_of") or "—", "raw_d1": d1, "raw_d30": _n(r.get("d30"))}


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _moved(x, up="עלה", down="ירד", flat="כמעט לא זז"):
    return flat if x is None or abs(x) < 0.3 else up if x > 0 else down


def summary(key: str, rows: list) -> str:
    """One plain sentence per section, built only from the verified values in it."""
    ok = {r["sym"]: r for r in rows if r["status"] == "ok"}
    if not ok:
        return "אין כרגע נתונים מאומתים בקבוצה הזו."
    if key == "equity":
        us = [ok[s] for s in US if s in ok]
        out = []
        if us:
            a = _avg([r["raw_d1"] for r in us])
            w = _moved(a, "עלו", "ירדו", "כמעט לא זזו")
            lead = (min(us, key=lambda r: r["raw_d1"]) if a is not None and a < 0 else max(us, key=lambda r: r["raw_d1"]))
            out.append(f"המדדים בארה״ב {w}" + (f", בעיקר {lead['name']}." if abs(a or 0) >= 0.3 else "."))
        intl = [ok[s] for s in ("^GDAXI", "^N225", "^FTSE", "^HSI") if s in ok]
        if intl:
            out.append(f"מחוץ לארה״ב הם {_moved(_avg([r['raw_d1'] for r in intl]), 'עלו', 'ירדו', 'כמעט לא זזו')}.")
        return " ".join(out)
    if key == "rates":
        out = []
        t = ok.get("^TNX")
        if t:
            out.append(f"תשואת האג״ח ל-10 שנים {_moved(t['raw_d1'], 'עלתה', 'ירדה', 'כמעט לא זזה')} ({t['d1']}), ל-{t['val']}.")
        u = ok.get("ILS=X")
        if u and u["raw_d1"] is not None:
            out.append("הדולר " + ("התחזק" if u["raw_d1"] >= 0.3 else "נחלש" if u["raw_d1"] <= -0.3 else "כמעט לא זז")
                       + f" מול השקל, {u['val']} שקלים לדולר.")
        return " ".join(out)
    if key == "commodity":
        out = []
        oil = [ok[s] for s in ("CL=F", "BZ=F") if s in ok]
        moves = {_moved(r["raw_d1"]) for r in oil}
        if len(oil) == 2 and moves == {"עלה", "ירד"}:          # the two benchmarks disagree: say so
            out.append(f"{oil[0]['name']} {_moved(oil[0]['raw_d1'])} ({oil[0]['d1']}) "
                       f"ו{oil[1]['name']} {_moved(oil[1]['raw_d1'])} ({oil[1]['d1']}).")
        elif oil:
            out.append(f"הנפט {_moved(_avg([r['raw_d1'] for r in oil]))}.")
        gold = ok.get("GC=F")
        if gold:
            out.append(f"הזהב {_moved(gold['raw_d1'])} ({gold['d1']}).")
        return " ".join(out)
    if key == "crypto":
        b = ok.get("BTC-USD")
        if not b:
            return ""
        return (f"הביטקוין {_moved(b['raw_d1'])} ביום האחרון ({b['d1']}) ו{_moved(b['raw_d30'])} בחודש האחרון ({b['d30']}). "
                f"נכון ל-{b['as_of']}, כי הקריפטו נסחר גם בסוף השבוע.")
    return ""


def sections(g: dict, advanced: bool = False) -> list:
    by = _by_symbol(g)
    out = []
    for key, title, base, extra in SECTIONS:
        syms = base + (extra if advanced else ())
        rows = [row(by[s]) for s in syms if s in by]
        note = ""
        if key == "rates":
            t2 = next((r for r in rows if r["sym"] == "2YY=F"), None)
            if t2 and t2["status"] != "ok":
                note = ("תשואת השנתיים חסרה במקור, ולכן גם עקום התשואות (ההפרש בין 10 שנים לשנתיים) "
                        "לא מוצג, במקום להציג מספר לא בדוק.")
        out.append({"key": key, "title": title, "summary": summary(key, rows), "rows": rows, "note": note,
                    "has_bp": any(r["sym"] in YIELDS for r in rows)})
    return out


def validation(g: dict) -> dict:
    """What was verified and what was not, for the transparency panel."""
    rows = [row(r) for r in _by_symbol(g).values() if r.get("symbol") != "CURVE"]
    return {"ok": sum(r["status"] == "ok" for r in rows),
            "issues": [{"name": r["name"], "status": r["status"], "why": r["why"]} for r in rows if r["status"] != "ok"],
            "updated": g.get("updated") or "—", "status": g.get("status")}


# ------------------------------------------------------------------ the system's own calculations
def _word(score):
    s = _n(score)
    if s is None:
        return "אין נתון", "muted"
    return (("חזק מאוד", "positive") if s >= 80 else ("חזק", "positive") if s >= 60 else ("ניטרלי", "warning") if s >= 40
            else ("חלש", "negative") if s >= 20 else ("חלש מאוד", "negative"))


def sectors(mkt: dict) -> dict:
    rows = []
    for s in sorted(mkt.get("sectors") or [], key=lambda s: -(_n(s.get("score")) or 0)):
        w, tone = _word(s.get("score"))
        rows.append({"name": s.get("sector"), "etf": s.get("etf"), "score": _n(s.get("score")), "word": w, "tone": tone,
                     "d1": H.pct(s.get("change_pct")), "m1": H.pct(s.get("ret_1m")), "m3": H.pct(s.get("ret_3m")),
                     "rs": H.pct(s.get("rs")), "trend": s.get("trend") or "—"})
    return {"up": [r for r in rows if (r["score"] or 0) >= 60], "down": [r for r in rows if r["score"] is not None and r["score"] < 40][::-1],
            "all": rows}


def breadth(mkt: dict) -> dict | None:
    b = mkt.get("breadth") or {}
    a50, a200 = _n(b.get("above50")), _n(b.get("above200"))
    adv, dec = _n(b.get("advancers")), _n(b.get("decliners"))
    if a50 is None and a200 is None:
        return None
    n = int((adv or 0) + (dec or 0)) or None
    share = lambda x: ("רוב המניות" if x >= 60 else "כחצי מהמניות" if x >= 40 else "מיעוט מהמניות") if x is not None else ""
    items = []
    if a50 is not None:
        items.append({"k": "מעל הממוצע של 50 יום", "v": f"{a50:.0f}%", "text": f"{share(a50)} במגמה קצרה חיובית"})
    if a200 is not None:
        items.append({"k": "מעל הממוצע של 200 יום", "v": f"{a200:.0f}%", "text": f"{share(a200)} במגמה ארוכה חיובית"})
    if adv is not None and n:
        up = adv / n * 100
        items.append({"k": "עלו ביום המסחר האחרון", "v": f"{up:.0f}%", "text": f"{int(adv)} מתוך {n}"})
    return {"n": n, "items": items, "method": b.get("method") or ""}


def gauges(mkt: dict, g: dict) -> list:
    """The hero's three numbers: the system's market score, fear and greed, and the VIX."""
    reg, fg = mkt.get("regime") or {}, mkt.get("fear_greed") or {}
    out = []
    if _n(reg.get("score")) is not None:
        out.append({"name": "ציון השוק של המערכת", "val": f"{reg['score']:.0f} מתוך 100", "chg": reg.get("label") or "",
                    "tone": "muted"})
    if _n(fg.get("score")) is not None:
        out.append({"name": "פחד וחמדנות", "val": f"{fg['score']:.0f} מתוך 100", "chg": fg.get("label") or "", "tone": "muted"})
    vix = _by_symbol(g).get("^VIX")
    if vix and g.get("status") == "ok" and not vix.get("suspect") and _n(vix.get("price")) is not None:
        out.append({"name": "מדד הפחד (VIX)", "val": f"{vix['price']:.2f}", "chg": H.pct(vix.get("d1")),
                    "tone": H.tone_of(vix.get("d1"), invert=True)})
    return out


def calc_age(mkt: dict, today: date | None = None) -> dict:
    try:
        d = datetime.strptime(str(mkt.get("date"))[:10], "%d/%m/%Y").date()
    except ValueError:
        return {"date": "לא ידוע", "stale": True}
    age = ((today or config.now_local().date()) - d).days
    return {"date": d.strftime("%d/%m/%Y"), "stale": age > STALE_DAYS, "age": age}


# ------------------------------------------------------------------ history (advanced mode)
HISTORY = ("^GSPC", "^IXIC", "^TNX", "ILS=X", "GC=F", "CL=F", "BTC-USD")
MATCH_TOL = 0.01           # on the same date, the live history must agree with the verified value within 1%


def _bp_change(last, then):
    d = round((last - then) * 100)
    return f"{'+' if d > 0 else '−' if d < 0 else ''}{abs(d)} נ״ב"


def history(hist: dict, g: dict) -> list:
    """3-month and 1-year change and the 52-week range for key assets, from a live
    price history. A series is shown only when its last close agrees with the value
    that passed today's validation, otherwise it is marked as needing verification."""
    by = _by_symbol(g)
    out = []
    for sym in HISTORY:
        s = (hist or {}).get(sym)
        name = NAMES.get(sym, sym)
        v = by.get(sym) or {}
        p = _n(v.get("price")) if g.get("status") == "ok" and not v.get("suspect") else None
        try:                                   # compare the same day the verified value describes
            as_of = datetime.strptime(str(v.get("as_of"))[:10], "%d/%m/%Y").date()
            s = s[[d.date() <= as_of for d in s.index]] if s is not None else s
        except ValueError:
            pass
        if s is None or len(s) < 253:
            out.append({"sym": sym, "name": name, "status": "missing", "why": "אין היסטוריה מספיקה מהמקור"})
            continue
        last = float(s.iloc[-1])
        if p is None:
            out.append({"sym": sym, "name": name, "status": "verify", "why": "אין ערך יומי מאומת להשוואה"})
            continue
        if abs(last / p - 1) > MATCH_TOL:
            out.append({"sym": sym, "name": name, "status": "verify", "why": "ההיסטוריה לא תואמת לנתון היומי המאומת"})
            continue
        yr = s.iloc[-252:]
        lo, hi = float(yr.min()), float(yr.max())
        if sym in YIELDS:
            ch = lambda back: _bp_change(last, float(s.iloc[-back]))
        else:
            ch = lambda back: H.pct((last / float(s.iloc[-back]) - 1) * 100)
        out.append({"sym": sym, "name": name, "status": "ok", "val": _val(sym, last),
                    "m3": ch(64), "y1": ch(253), "lo": _val(sym, lo), "hi": _val(sym, hi),
                    "pos": round((last - lo) / (hi - lo) * 100) if hi > lo else None})
    return out
