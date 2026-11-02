# -*- coding: utf-8 -*-
"""Company analysis view model (V4). Pure functions, no Streamlit, so they are tested.

Owner rules (01/11/2026), enforced here:
  * The decision is the LIVE engine's verdict for the same row the home and
    opportunities screens use (stockdata.verdicts), so a stock reads the same
    everywhere for the same close.
  * The live engine decides on three things only: company quality (Score V2),
    trend, and risk, behind a data-reliability gate. Price and analyst targets are
    shown in their own section and labelled as NOT part of that decision.
  * No buy price or target is produced here. Analyst targets are shown as what
    they are: an outside estimate. Conflicting signals are explained, not hidden.
  * Missing, old or unverified data is said plainly. Nothing is filled in.
"""
from datetime import date, datetime
from statistics import median

from dashboard.v4 import home_data as H
from dashboard.v4 import names_he as NH

_n = H._n
Q_STRONG, REL_MIN = 68, 55          # the live engine's thresholds (verdict.py)


# ------------------------------------------------------------------ formatting
def big_money(v):
    v = _n(v)
    if v is None:
        return "—"
    a, s = abs(v), "−" if v < 0 else ""
    for div, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if a >= div:
            return f"{s}${a / div:,.2f}{unit}" if a / div < 10 else f"{s}${a / div:,.1f}{unit}"
    return f"{s}${a:,.0f}"


def num(v, digits=1):
    v = _n(v)
    return "—" if v is None else f"{v:,.{digits}f}"


def pct1(v, plus=True):
    v = _n(v)
    if v is None:
        return "—"
    sign = "+" if plus and v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.1f}%"


def _dmy(s):
    """Any stored date (ISO or DD/MM/YYYY) as DD/MM/YYYY, or None."""
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(s)[:10], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


def _age(s, today=None):
    d = _dmy(s)
    if not d:
        return None
    return ((today or date.today()) - datetime.strptime(d, "%d/%m/%Y").date()).days


# ------------------------------------------------------------------ header
def _below_high(d):
    """DistFromHigh% is (52-week high - price) / high, so 0 at the high and positive below it."""
    d = _n(d)
    if d is None:
        return "—"
    return "בשיא" if d < 0.5 else f"{d:.1f}% מתחת לשיא"


def header(t: str, row: dict, prof: dict, info: dict) -> dict:
    row, prof, info = row or {}, prof or {}, info or {}
    name = H.short_name(row.get("Name") or info.get("longName") or info.get("shortName"), t)
    sector = H.sector_he(row if row.get("Sector") else {"Sector": prof.get("sector") or info.get("sector")})
    price = _n(row.get("Price"))
    return {
        "ticker": t, "name": name, "ini": (name or t)[:1].upper(), "sector": sector,
        # Hebrew only: an industry or country without a Hebrew name is left out, not shown in English.
        "industry": NH.industry(prof.get("industry") or info.get("industry")), "country": NH.country(info.get("country")),
        "price": H.money(price), "chg": H.pct(row.get("DailyChange%")), "chg_tone": H.tone_of(row.get("DailyChange%")),
        "close": _dmy(row.get("Date")) or "—",
        "market_cap": big_money(prof.get("market_cap") or row.get("MarketCap")),
        "fund_date": row.get("FundDate"),
        "stale": H.stale_note(row),
        "high52": H.money(row.get("High52w")),
        "dist_high": _below_high(row.get("DistFromHigh%")),
    }


# ------------------------------------------------------------------ decision
HEADLINES = {
    ("buy", None): "חברה חזקה, והמגמה של המניה תומכת.",
    ("wait", "down"): "חברה חזקה, אבל המניה במגמת ירידה.",
    ("wait", "risk"): "חברה חזקה, אבל הסיכון גבוה מאוד.",
    ("wait", "fair"): "חברה סבירה, אבל עוד לא חזקה מספיק.",
    ("wait", "weak"): "החברה עוד לא חזקה מספיק.",
    ("avoid", "poor"): "הנתונים העסקיים חלשים מדי.",
    ("avoid", "down"): "מגמת ירידה, בלי חברה חזקה מספיק כדי לפצות.",
    ("avoid", "risk"): "סיכון גבוה מאוד ביחס לאיכות החברה.",
    ("nodata", None): "אין מספיק מידע אמין להערכת השקעה.",
}
QUALITY_ANSWER = {"strong": ("כן, חזקה", "positive"), "fair": ("סבירה", "warning"),
                  "weak": ("חלשה", "negative"), "poor": ("חלשה מאוד", "negative")}


def _case(v: dict, row: dict) -> tuple:
    a, tier, trend = v.get("action"), v.get("quality_tier"), v.get("trend")
    very_high = row.get("RiskLevel") == "גבוה מאוד"
    if a == "wait":
        return ("wait", "down" if tier == "strong" and trend == "down" else "risk" if tier == "strong" and very_high
                else "fair" if tier == "fair" else "weak")
    if a == "avoid":
        return ("avoid", "poor" if tier == "poor" else "down" if trend == "down" else "risk")
    return (a if a in ("buy", "nodata") else "nodata", None)


# The engine's holder guidance as a state of the data, not an instruction to buy or sell
# (the system does not know the visitor's portfolio or situation).
HOLDER_STATE = {"hold": "התמונה תקינה", "caution": "שווה לעקוב", "review_sell": "התמונה נחלשה", "nodata": "אין מספיק נתונים"}


def decision(v: dict | None, row: dict) -> dict:
    """The live verdict, told in the order a reader needs it."""
    if not v:
        return {"status": "unknown", "label": "המניה לא במעקב של המערכת", "tone": "muted",
                "headline": "אין הערכת השקעה למניה הזו.",
                "why": "המערכת נותנת הערכת השקעה רק למניות במדד S&P 500 שעברו ניתוח עסקי מלא.",
                "answers": [], "conditions": [], "pros": [], "cons": [], "holder": None}
    tier = v.get("quality_tier")
    qa = QUALITY_ANSWER.get(tier, ("אין מספיק מידע", "muted"))
    status = "nodata" if v["action"] == "nodata" else "rated"
    why = v.get("why") or ""
    if status == "nodata" and (row or {}).get("_tier") == "technical":
        why = ("המניה לא נכללה היום בניתוח המלא (רק כ-58 מתוך 500 מניות נכללות), ולכן אין לה ציון איכות. "
               "הניתוח היומי בוחר את המניות לפי תנועת המחיר האחרונה, יחד עם רשימת המעקב הקבועה. "
               "בלי ציון איכות אין הערכת השקעה, והמערכת לא מנחשת אחת. המחיר, הגרף והנתונים שנשמרו מוצגים בהמשך, למידע בלבד.")
    answers = [
        {"q": "האם זו חברה חזקה?", "a": qa[0], "tone": qa[1]},
        {"q": "האם לשקול קנייה היום?", "a": v["label"], "tone": v["tone"]},
    ]
    return {
        "status": status, "action": v["action"], "label": v["label"], "tone": v["tone"],
        "headline": HEADLINES.get(_case(v, row), ""), "why": why,
        "answers": answers if status == "rated" else [],
        "conditions": list(v.get("conditions") or []),
        "pros": list(v.get("pros") or []), "cons": list(v.get("cons") or []),
        "holder": ({"label": HOLDER_STATE.get(v["holder"], v["holder_label"]), "tone": v["holder_tone"],
                    "why": v["holder_why"].replace(" אין סיבה מהנתונים לשנות את ההחזקה.", "")
                    .replace("אין סיבה למכור, אבל כדאי לא להגדיל את הפוזיציה כרגע.", "יש סימן אחד או יותר שכדאי לעקוב אחריו.")}
                   if status == "rated" else None),
    }


def checks(v: dict | None, row: dict) -> list:
    """The live engine's actual gates for 'consider buying', each with its value.
    These are the only things that decide the verdict. ok is None when the input is
    missing: unknown is shown as unknown, not as a failure. A stock that was not in the
    full analysis has no checks to show (a passing reliability row beside "not enough
    reliable information" only confused readers)."""
    if not v or (row or {}).get("_tier") == "technical":
        return []
    q, rel = _n(v.get("quality")), (v.get("reliability") or {}).get("score")
    p, m200 = _n(row.get("Price")), _n(row.get("MA200"))
    risk = row.get("RiskLevel")
    out = [{
        "name": "אמינות הנתונים", "rule": f"לפחות {REL_MIN} מתוך 100, אחרת אין הערכה",
        "value": "—" if rel is None else f"{rel} מתוך 100", "ok": None if rel is None else rel >= REL_MIN,
        "plain": "יש מספיק נתונים אמינים" if rel is not None and rel >= REL_MIN else "חסרים נתונים אמינים",
    }, {
        "name": "איכות החברה", "rule": f"ציון איכות של {Q_STRONG} ומעלה",
        "value": "אין ציון" if q is None else f"{q:.0f} מתוך 100", "ok": None if q is None else q >= Q_STRONG,
        "plain": {"strong": "חברה חזקה", "fair": "חברה סבירה, מתחת לסף", "weak": "חברה חלשה",
                  "poor": "חברה חלשה מאוד"}.get(v.get("quality_tier"), "אין ציון איכות"),
    }, {
        "name": "מגמה", "rule": "המחיר לא מתחת לממוצע של 200 יום",
        "value": ("אין נתון" if p is None or m200 is None else
                  f"{H.money(p)}, {'מעל ממוצע' if p >= m200 else 'מתחת לממוצע'} 200 יום ({H.money(m200)})"),
        "ok": None if v.get("trend") in (None, "unknown") else v.get("trend") != "down",
        "plain": {"up": "במגמת עלייה", "mixed": "מעל הממוצע ארוך הטווח, מעורבת בטווח הקצר",
                  "down": "במגמת ירידה", "unknown": "אין נתון מגמה"}.get(v.get("trend"), "אין נתון מגמה"),
    }, {
        "name": "סיכון", "rule": "רמת סיכון לא \"גבוה מאוד\"",
        "value": risk or "אין נתון", "ok": None if risk is None else risk != "גבוה מאוד",
        "plain": (f"רמת סיכון {risk}, הסף הוא \"גבוה מאוד\"" if risk and risk != "גבוה מאוד" else
                  f"רמת סיכון {risk}" if risk else "אין נתון סיכון"),
    }]
    return out


PARTS = (("ContribFund", "fundamental", "נתונים עסקיים", "ScoreFundamental"),
         ("ContribTech", "technical", "מצב טכני (מומנטום)", "Score"),
         ("ContribSector", "sector", "חוזק הענף (מומנטום)", "SectorScore"),
         ("ContribNews", "news", "חדשות", "ScoreNews"),
         ("ContribRisk", "risk", "סיכון נמוך", "RiskScore"))


def score_parts(row: dict) -> dict | None:
    """What the quality score is made of: stored contributions (full analysis) or
    the same composite recomputed, used only when it reproduces the live score."""
    q = _n(row.get("ScoreV2"))
    if q is None or row.get("_tier") not in ("full", "enriched"):
        return None
    if all(_n(row.get(c)) is not None for c, *_ in PARTS):
        parts = [{"name": lbl, "pts": _n(row[c]), "raw": _n(row.get(src))} for c, _, lbl, src in PARTS]
    else:
        from ranking_engine.composite import composite_score
        news = _n(row.get("ScoreNews"))
        comp = composite_score(technical=_n(row.get("Score")), fundamental=_n(row.get("ScoreFundamental")),
                               sector=_n(row.get("SectorScore")), news=50 if news is None else news,
                               risk=_n(row.get("RiskScore")))
        if not comp or abs(comp["final"] - q) > 1:
            return None
        parts = [{"name": lbl, "pts": comp["contributions"].get(k), "raw": comp["raw"].get(k)}
                 for _, k, lbl, _ in PARTS if k in comp["contributions"]]
    mom = sum(p["pts"] or 0 for p in parts if "מומנטום" in p["name"])
    return {"total": q, "parts": parts, "momentum_pts": round(mom, 1), "momentum_share": round(mom / q * 100) if q else None}


# ------------------------------------------------------------------ two sources, one story
DIFF_FIELDS = (("TargetMean", "target_mean", "יעד אנליסטים ממוצע", "money"),
               ("RevenueGrowth", "rev_growth", "צמיחת מכירות (רבעון מול אשתקד)", "pct"),
               ("OperatingMargin", "op_margin", "רווח תפעולי מהמכירות", "pct"),
               ("EPSGrowth", "eps_growth", "צמיחת רווח למניה (רבעון מול אשתקד)", "pct"),
               ("DebtToEquity", "debt_equity", "חוב להון", "ratio"),
               ("ForwardPE", "fwd_pe", "מכפיל רווח עתידי", "ratio"))


def _fmt(v, kind):
    return H.money(v) if kind == "money" else pct1(v) if kind == "pct" else num(v, 2)


def diffs(row: dict, prof: dict) -> list:
    """Fields where the stored company profile (often a day or two newer) differs
    from the daily scan the verdict was built on. The page keeps the verdict's
    numbers and lists the newer ones, so nothing contradicts silently."""
    out = []
    try:
        fd = datetime.strptime(str((row or {}).get("FundDate"))[:10], "%d/%m/%Y").date()
        pdt = datetime.strptime(_dmy((prof or {}).get("_date")) or "", "%d/%m/%Y").date()
    except ValueError:
        return out                       # without both dates we cannot say which is newer
    if pdt <= fd:
        return out                       # the verdict's own data is the newer one
    for rk, pk, name, kind in DIFF_FIELDS:
        a, b = _n((row or {}).get(rk)), _n((prof or {}).get(pk))
        if a is None or b is None:
            continue
        if abs(a - b) > max(abs(a), abs(b), 1) * (0.03 if kind == "money" else 0.08):
            out.append({"name": name, "scan": _fmt(a, kind), "newer": _fmt(b, kind), "key": rk})
    return out


def _first(row, rk, prof, pk):
    a = _n((row or {}).get(rk)) if rk else None
    return a if a is not None else _n((prof or {}).get(pk))


# ------------------------------------------------------------------ price and valuation
MULTIPLES = (
    ("fwd_pe", "ForwardPE", "מכפיל רווח עתידי", "כמה משלמים על כל דולר רווח שהאנליסטים צופים לשנה הקרובה. מבוסס על תחזית."),
    ("trailing_pe", None, "מכפיל רווח (12 חודשים אחרונים)", "כמה משלמים על כל דולר רווח שהחברה כבר הרוויחה."),
    ("peg", "PEG", "PEG", "מכפיל הרווח ביחס לקצב צמיחת הרווח. סביב 1 נחשב מאוזן."),
    ("ps", None, "מכפיל מכירות", "שווי החברה ביחס למכירות השנתיות."),
    ("ev_ebitda", None, "EV/EBITDA", "שווי החברה כולל חוב, ביחס לרווח התפעולי לפני פחת."),
)


def price_flag(v: dict | None, gap, flabel: str, conflicts: list, above=None) -> str:
    """The single most important tension between the verdict and the price data,
    in one line, or "" when they do not pull apart."""
    a = (v or {}).get("action")
    if a == "buy" and above is not None and above >= 1:
        return f"המחיר כבר גבוה ב-{above:.0f}% מהיעד הממוצע של האנליסטים."
    if a == "buy" and "גבוה" in flabel:
        return "לפי הערכת המחיר של המערכת, המחיר גבוה."
    if a in ("wait", "avoid") and gap is not None and gap >= 15:
        return f"היעד הממוצע של האנליסטים גבוה ב-{gap:.0f}% מהמחיר, אבל הערכת ההשקעה לא תומכת בקנייה כרגע."
    if conflicts:
        return "יש בנתוני התמחור סימנים שלא מסתדרים זה עם זה."
    return ""


def price_section(v: dict | None, row: dict, prof: dict) -> dict:
    row, prof = row or {}, prof or {}
    lv = (v or {}).get("levels") or {}
    price = _n(row.get("Price")) or _n(prof.get("price"))
    src = "row" if _n(row.get("TargetMean")) is not None else "profile"
    tgt = _n(lv.get("target")) or _n(row.get("TargetMean")) or _n(prof.get("target_mean"))
    lo = _n(lv.get("target_low")) or _n(row.get("TargetLow")) or _n(prof.get("target_low"))
    hi = _n(lv.get("target_high")) or _n(row.get("TargetHigh")) or _n(prof.get("target_high"))
    n = _n(lv.get("analysts")) or _n(row.get("AnalystCount")) or _n(prof.get("analysts"))
    gap = round((tgt / price - 1) * 100, 1) if tgt and price else None        # the target, measured from the price
    above = round((price / tgt - 1) * 100, 1) if tgt and price else None      # the price, measured from the target

    analysts = None
    if tgt and price:
        lo_ = min(x for x in (lo, tgt, price) if x)
        hi_ = max(x for x in (hi, tgt, price) if x)
        span = (hi_ - lo_) or 1
        pos = lambda x: round((x - lo_) / span * 100, 1) if x else None
        analysts = {"mean": H.money(tgt), "low": H.money(lo), "high": H.money(hi), "n": int(n) if n else None,
                    "gap": gap, "gap_txt": pct1(gap), "price": H.money(price),
                    "pos": {"price": pos(price), "mean": pos(tgt), "low": pos(lo), "high": pos(hi)},
                    "plain": (f"היעד הממוצע של האנליסטים גבוה ב-{gap:.0f}% מהמחיר." if gap >= 1 else
                              f"המחיר גבוה ב-{above:.0f}% מהיעד הממוצע של האנליסטים." if gap <= -1 else
                              "המחיר כמעט זהה ליעד הממוצע של האנליסטים.")}

    facet = ((v or {}).get("facets") or {}).get("price") or {}
    mults = []
    for key, rkey, name, expl in MULTIPLES:
        val = _first(row, rkey, prof, key)
        mults.append({"key": key, "name": name, "val": num(val), "raw": val, "expl": expl})
    pe_hist = [x for x in (prof.get("pe_hist") or []) if _n(x) is not None and x > 0]
    own = None
    tpe = _n(prof.get("trailing_pe"))
    if len(pe_hist) >= 3 and tpe:
        m = median(pe_hist)
        own = {"now": num(tpe), "median": num(m), "years": len(pe_hist),
               "plain": (f"מכפיל הרווח היום ({tpe:.0f}) {'נמוך' if tpe < m else 'גבוה'} מהחציון שלה בסוף "
                         f"{len(pe_hist)} השנים הפיסקליות האחרונות ({m:.0f}).")}

    conflicts = []
    flabel = facet.get("label") or ""
    if gap is not None and "אטרקטיבי" in flabel and gap < 0:
        conflicts.append("ציון התמחור של המערכת אומר \"מחיר אטרקטיבי\", אבל המחיר כבר גבוה מהיעד הממוצע של האנליסטים. "
                         "שני המקורות מודדים דברים שונים: ציון התמחור משווה את מכפיל הרווח לקצב הצמיחה, "
                         "ויעד האנליסטים הוא הערכה למחיר בעוד כשנה. אין ביניהם הכרעה, ושניהם לא משנים את הערכת ההשקעה.")
    if gap is not None and "גבוה" in flabel and gap >= 15:
        conflicts.append("ציון התמחור של המערכת אומר \"מחיר גבוה\", אבל האנליסטים צופים מחיר גבוה ב-"
                         f"{gap:.0f}% בממוצע. מכפילים גבוהים לצד צפי לצמיחה מהירה יוצרים את הפער הזה.")
    if lo and hi and lo > 0 and hi / lo >= 1.8:
        conflicts.append(f"האנליסטים חלוקים מאוד: היעד הנמוך {H.money(lo)} והגבוה {H.money(hi)}. "
                         "ככל שהטווח רחב יותר, היעד הממוצע פחות אומר.")
    if n is not None and n < 5 and tgt:
        conflicts.append(f"רק {int(n)} אנליסטים מכסים את המניה, ולכן היעד הממוצע פחות יציב.")
    newer = next((x for x in diffs(row, prof) if x["key"] == "TargetMean"), None)
    if newer and analysts:
        conflicts.append(f"היעד הממוצע השתנה מאז הסריקה: בסריקה שעליה נשענת ההערכה {newer['scan']}, "
                         f"ובעדכון של {_dmy(prof.get('_date'))} {newer['newer']}. כאן מוצג היעד של הסריקה, כדי שהכול יתאים להערכה.")
    if own and analysts and "גבוה" in own["plain"] and gap is not None and gap >= 10:
        conflicts.append("ביחס להיסטוריה של עצמה המניה יקרה מהרגיל, אבל האנליסטים צופים עלייה. "
                         "זה קורה כשמצפים שהרווחים יגדלו מהר יותר מבעבר.")
    return {
        "flag": price_flag(v, gap, flabel, conflicts, above),
        "price": H.money(price), "analysts": analysts,
        "facet": {"label": flabel or "אין מספיק מידע", "tone": facet.get("tone") or "muted", "basis": facet.get("basis") or ""},
        "multiples": mults, "own_history": own, "conflicts": conflicts,
        "target_source": src, "has_any": bool(analysts or any(m["raw"] is not None for m in mults)),
    }


# ------------------------------------------------------------------ business
def _year(s):
    d = _dmy(s)
    return d[-4:] if d else None


def business(prof: dict, row: dict) -> dict:
    """Annual history (past, from the filed statements) and the latest 12 months."""
    prof, row = prof or {}, row or {}
    years = [_year(x) for x in (prof.get("fy_ends") or [])]
    hist = []
    for i, y in enumerate(years):
        if not y:
            continue
        g = lambda k: (prof.get(k) or [None] * 9)[i] if i < len(prof.get(k) or []) else None
        hist.append({"year": y, "rev": _n(g("rev_hist")), "opm": _n(g("op_margin_hist")),
                     "eps": _n(g("eps_hist")), "fcf": _n(g("fcf_hist"))})
    hist = [h for h in hist if any(h[k] is not None for k in ("rev", "opm", "eps", "fcf"))][::-1]   # oldest first
    top = max([h["rev"] for h in hist if h["rev"]] or [0])
    for i, h in enumerate(hist):
        h["rev_txt"], h["opm_txt"] = big_money(h["rev"]), pct1(h["opm"], plus=False)
        h["eps_txt"], h["fcf_txt"] = (f"${h['eps']:.2f}" if h["eps"] is not None else "—"), big_money(h["fcf"])
        h["w"] = f"{max(4, (h['rev'] or 0) / top * 100):.0f}%" if top else "0%"
        prev = hist[i - 1]["rev"] if i else None
        h["growth"] = pct1((h["rev"] / prev - 1) * 100) if h["rev"] and prev else ""

    g = lambda pk, rk=None: _first(row, rk, prof, pk)
    rev, opm, pm = g("revenue"), g("op_margin", "OperatingMargin"), g("profit_margin")
    rg, eg = g("rev_growth", "RevenueGrowth"), g("eps_growth", "EPSGrowth")
    roe, de, fcf = g("roe"), g("debt_equity", "DebtToEquity"), g("fcf")
    debt, cash = g("total_debt"), g("total_cash")
    fcf_m = round(fcf / rev * 100, 1) if fcf is not None and rev else None

    lines = []
    if rg is not None:
        amt = f"{abs(rg):.0f}" if abs(rg) >= 1 else f"{abs(rg):.1f}"
        lines.append({"k": "צמיחה", "tone": "positive" if rg >= 10 else "warning" if rg >= 0 else "negative",
                      "text": (f"ברבעון האחרון המכירות {'גדלו' if rg >= 0 else 'ירדו'} ב-{amt}% לעומת הרבעון המקביל אשתקד."
                               + (f" מכירות 12 החודשים האחרונים: {big_money(rev)}." if rev else ""))})
    if opm is not None:
        lines.append({"k": "רווחיות", "tone": "positive" if opm >= 20 else "warning" if opm >= 8 else "negative",
                      "text": f"מכל 100 דולר מכירות נשארים כ-{opm:.0f} דולר רווח תפעולי."})
    if fcf_m is not None:
        lines.append({"k": "מזומנים", "tone": "positive" if fcf_m >= 10 else "warning" if fcf_m >= 0 else "negative",
                      "text": (f"החברה מייצרת מזומנים: תזרים חופשי של {fcf_m:.0f}% מהמכירות." if fcf_m >= 0 else
                               "החברה שורפת מזומנים: התזרים החופשי שלילי.")})
    if de is not None:
        lines.append({"k": "חוב", "tone": "positive" if de <= 0.5 else "warning" if de <= 1.5 else "negative",
                      "text": (f"חוב נמוך ביחס להון (פי {de:.1f})." if de <= 0.5 else
                               f"חוב בינוני ביחס להון (פי {de:.1f})." if de <= 1.5 else
                               f"חוב גבוה ביחס להון (פי {de:.1f}).")})
    metrics = [
        {"k": "מכירות (12 חודשים)", "v": big_money(rev)}, {"k": "צמיחת מכירות (רבעון מול אשתקד)", "v": pct1(rg)},
        {"k": "רווח תפעולי מהמכירות", "v": pct1(opm, plus=False)}, {"k": "רווח נקי מהמכירות", "v": pct1(pm, plus=False)},
        {"k": "צמיחת רווח למניה (רבעון מול אשתקד)", "v": pct1(eg)}, {"k": "תשואה על ההון (ROE)", "v": pct1(roe, plus=False)},
        {"k": "תזרים חופשי", "v": big_money(fcf)}, {"k": "חוב להון", "v": num(de, 2)},
        {"k": "חוב", "v": big_money(debt)}, {"k": "מזומנים", "v": big_money(cash)},
    ]
    note = ""
    last = next((h for h in reversed(hist) if h["growth"]), None)
    if rg is not None and last and hist[-1]["rev"] and len(hist) >= 2 and hist[-2]["rev"]:
        annual = (hist[-1]["rev"] / hist[-2]["rev"] - 1) * 100
        if abs(rg - annual) >= 20 or (rg >= 5 and annual <= -5) or (rg <= -5 and annual >= 5):
            note = (f"הצמיחה ברבעון האחרון ({pct1(rg)}) שונה מאוד מהשינוי השנתי האחרון ({pct1(annual)} ב-{hist[-1]['year']}). "
                    "נתון של רבעון אחד יכול להיות תנודתי, ולכן כדאי לקרוא את שניהם יחד.")
    return {"hist": hist, "lines": lines, "metrics": metrics, "date": _dmy(prof.get("_date")),
            "has_hist": bool(hist), "has_any": bool(lines) or bool(hist), "note": note}


# ------------------------------------------------------------------ risks
def risks(v: dict | None, row: dict, events: dict, t: str, today: date | None = None) -> dict:
    from deepdive import SECTOR_RISK_HE
    row, today = row or {}, today or date.today()
    items = []
    lvl = row.get("RiskLevel")
    vol, dd, beta = _n(row.get("Volatility")), _n(row.get("MaxDrawdown")), _n(row.get("Beta"))
    ev = (events or {}).get(t) or {}
    ed = ev.get("earnings_date")
    try:
        days = (datetime.strptime(str(ed)[:10], "%Y-%m-%d").date() - today).days if ed else None
    except ValueError:
        days = None
    if days is not None and 0 <= days <= 14:
        when = "היום" if days == 0 else "מחר" if days == 1 else f"בעוד {days} ימים"
        items.append({"tone": "warning", "title": f"דוחות כספיים {when} ({_dmy(ed)})",
                      "text": "ביום דוחות המחיר יכול לזוז בחדות, לשני הכיוונים."})
    if dd is not None and dd <= -30:
        items.append({"tone": "negative", "title": f"ירידה חדה בעבר: {pct1(dd)}",
                      "text": "זו הירידה הגדולה ביותר מהשיא שנמדדה בשנה האחרונה. זה מה שהמניה כבר עשתה, לא תחזית."})
    rsi, r1m = _n(row.get("RSI14")), _n(row.get("Ret1m"))
    if rsi is not None and rsi >= 75:
        items.append({"tone": "warning", "title": "עלתה מהר מאוד לאחרונה",
                      "text": (f"עלייה של {pct1(r1m)} בחודש האחרון. " if r1m is not None else "")
                      + "אחרי עלייה מהירה, תנודות חדות סבירות יותר. המחקר של המערכת לא מצא שזה מנבא ירידה."})
    dsup = _n(row.get("DistSupport%"))
    if dsup is not None and abs(dsup) >= 15:
        items.append({"tone": "muted", "title": f"רמת התמיכה רחוקה: {H.money(row.get('Support'))}",
                      "text": f"כ-{abs(dsup):.0f}% מתחת למחיר. אם המגמה תתהפך, אין רמה טכנית קרובה שבה המחיר נעצר בעבר."})
    for c in ((v or {}).get("cons") or []):
        if c.startswith("דוחות") or "מגמת ירידה" in c or "עלתה מהר" in c:
            continue
        items.append({"tone": "warning", "title": c, "text": ""})
    rel = (v or {}).get("reliability") or {}
    sec = SECTOR_RISK_HE.get(row.get("Sector")) if row.get("Sector") else None
    return {
        "level": lvl or "אין נתון", "level_tone": H.RISK.get(lvl, "muted"),
        "metrics": [{"k": "תנודתיות שנתית (שנה אחרונה)", "v": pct1(vol, plus=False)}, {"k": "ירידה מקסימלית (שנה אחרונה)", "v": pct1(dd)},
                    {"k": "בטא (רגישות לשוק)", "v": num(beta, 2)}],
        "items": items[:6], "sector": sec or [],
        "reliability": {"score": rel.get("score"), "label": rel.get("label"), "reasons": rel.get("reasons") or []},
    }


# ------------------------------------------------------------------ about and sources
def about(t: str, row: dict, prof: dict, info: dict) -> dict:
    info, prof = info or {}, prof or {}
    hd = header(t, row, prof, info)
    he_line = f"{hd['name']} פועלת בענף {hd['sector']}"
    if hd["industry"]:
        he_line += f", בתחום {hd['industry']}"
    if hd["country"]:
        he_line += f". מטה החברה: {hd['country']}"
    emp = _n(info.get("fullTimeEmployees"))
    return {"line": he_line + ".", "summary_he": info.get("summary_he"), "summary_en": info.get("longBusinessSummary"),
            "employees": f"{emp:,.0f}" if emp else None, "website": info.get("website")}


def sources(row: dict, prof: dict, live: dict, today: date | None = None) -> list:
    today = today or date.today()
    row = row or {}
    out = [{"what": "חישוב הערכת ההשקעה", "src": "הסריקה היומית, לפי מחיר הסגירה",
            "date": _dmy(row.get("Date")) or "—", "ok": bool(row)},
           {"what": "הנתונים העסקיים שעליהם נשענת ההערכה: מתי נשלפו", "src": "Yahoo Finance",
            "date": row.get("FundDate") or "לא נשמר", "ok": bool(row.get("FundDate"))},
           {"what": "התקופה שהנתונים העסקיים מתארים", "src": "Yahoo Finance (הרבעון האחרון בנתונים)",
            "date": f"רבעון עד {row['LastQuarter']}" if row.get("LastQuarter") else "לא נשמר",
            "ok": bool(row.get("LastQuarter"))},
           {"what": "הדוח הכספי האחרון שפורסם", "src": "Yahoo Finance (מועדי דוחות)",
            "date": row.get("LastReport") or "לא נשמר", "ok": bool(row.get("LastReport"))}]
    pd_ = _dmy((prof or {}).get("_date"))
    age = _age((prof or {}).get("_date"), today)
    out.append({"what": "נתונים עסקיים, מכפילים והיסטוריה שנתית", "src": "Yahoo Finance, דוחות שנתיים",
                "date": pd_ or "לא זמין", "ok": bool(prof),
                "note": (f"בני {age} ימים" if age is not None and age > 7 else "")})
    out.append({"what": "יעדי אנליסטים", "src": "Yahoo Finance (ממוצע תחזיות)",
                "date": _dmy((row or {}).get("Date")) if _n((row or {}).get("TargetMean")) is not None else (pd_ or "לא זמין"),
                "ok": _n((row or {}).get("TargetMean")) is not None or _n((prof or {}).get("target_mean")) is not None})
    out.append({"what": "גרף מחירים ותיאור החברה", "src": "Yahoo Finance, שליפה חיה",
                "date": (live or {}).get("fetched") or "לא זמין", "ok": bool((live or {}).get("ok"))})
    return out
