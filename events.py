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
                action = str(last.get("Action", "")).lower()
                he = {"up": "שדרוג", "down": "הורדת דירוג",
                      "init": "כיסוי חדש", "main": "אישרור"}.get(action, action or "עדכון")
                out["rating_action"] = (f"{he}: {last.get('FromGrade','')} → "
                                        f"{last.get('ToGrade','')}").strip(" :→")
                out["rating_firm"] = str(last.get("Firm", "")) or None
    except Exception:
        pass

    return out
