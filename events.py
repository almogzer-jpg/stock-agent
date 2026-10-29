# -*- coding: utf-8 -*-
"""Per-ticker corporate events from yfinance (free, best-effort).

Provides earnings dates and the latest analyst rating action — used for
catalysts/risks (Phase 5) and the Alert Center (Phase 8). yfinance's calendar
and upgrades/downgrades feeds are sometimes empty or slow, so every field is
best-effort and returns None when unavailable (we never fabricate).
"""
from datetime import datetime, date

try:
    import yfinance as yf
except ImportError:
    yf = None


def _days_until(d) -> int | None:
    try:
        if isinstance(d, datetime):
            d = d.date()
        if isinstance(d, date):
            return (d - date.today()).days
    except Exception:
        pass
    return None


def days_phrase(n) -> str:
    """Hebrew 'when' phrase for a day count: 0 → היום, 1 → מחר, else בעוד N ימים."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return "היום"
    if n == 1:
        return "מחר"
    return f"בעוד {n} ימים"


GRADE_HE = {
    "strong buy": "קנייה חזקה", "buy": "קנייה", "accumulate": "צבירה",
    "outperform": "תשואת-יתר", "market outperform": "תשואת-יתר",
    "sector outperform": "תשואת-יתר", "overweight": "משקל-יתר", "positive": "חיובי",
    "hold": "החזקה", "neutral": "ניטרלי", "equal-weight": "משקל-שוק",
    "market perform": "תשואת-שוק", "sector perform": "תשואת-שוק",
    "peer perform": "תשואת-שוק", "in-line": "בקו השוק", "sector weight": "משקל-שוק",
    "underperform": "תשואת-חסר", "market underperform": "תשואת-חסר",
    "underweight": "משקל-חסר", "reduce": "הקטנה", "negative": "שלילי",
    "sell": "מכירה", "strong sell": "מכירה חזקה",
}
ACTION_HE = {"up": "שדרוג", "down": "הורדת דירוג", "init": "כיסוי חדש",
             "main": "אישרור דירוג", "reit": "אישרור דירוג"}


def grade_he(grade) -> str:
    g = str(grade or "").strip()
    return GRADE_HE.get(g.lower(), g)


def rating_action_he(action, from_grade, to_grade) -> str:
    """One readable Hebrew line for an analyst rating action (RTL arrow)."""
    he = ACTION_HE.get(str(action or "").lower(), "עדכון דירוג")
    frm, to = grade_he(from_grade), grade_he(to_grade)
    if not frm or frm == to:
        return f"{he}: {to}" if to else he
    return f"{he}: {frm} ← {to}"


def get_events(symbol: str) -> dict:
    """Return {earnings_date, days_to_earnings, rating_action, rating_firm}.

    All fields best-effort; missing data -> None.
    """
    out = {"earnings_date": None, "days_to_earnings": None,
           "rating_action": None, "rating_firm": None}
    if yf is None:
        return out
    tk = yf.Ticker(symbol)

    # --- Earnings date (next upcoming) ---
    try:
        cal = tk.calendar
        ed = None
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if isinstance(ed, (list, tuple)) and ed:
                ed = ed[0]
        if ed is not None:
            dni = _days_until(ed)
            if dni is not None and dni >= 0:
                out["earnings_date"] = str(getattr(ed, "date", lambda: ed)())[:10] \
                    if hasattr(ed, "date") else str(ed)[:10]
                out["days_to_earnings"] = dni
    except Exception:
        pass

    # --- Latest analyst rating action (upgrade/downgrade) ---
    try:
        ud = tk.upgrades_downgrades
        if ud is not None and len(ud):
            ud = ud.sort_index()                 # index = GradeDate
            last = ud.iloc[-1]
            gdate = ud.index[-1]
            recent = _days_until(getattr(gdate, "to_pydatetime", lambda: gdate)())
            # Only surface if within the last ~14 days.
            if recent is not None and -14 <= recent <= 0:
                out["rating_action"] = rating_action_he(
                    last.get("Action"), last.get("FromGrade"), last.get("ToGrade"))
                out["rating_firm"] = str(last.get("Firm", "")) or None
    except Exception:
        pass

    return out
