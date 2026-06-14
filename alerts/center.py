# -*- coding: utf-8 -*-
"""Alert Center (Phase 8) — generate typed alerts from real signals.

Alert types: breakout, volume spike, earnings, analyst upgrade/downgrade,
sector rotation. Each alert is a dict {type, scope, severity, message}.
All derived from real scan data, sector intelligence, and events.
"""


def build_alerts(df, sectors: list | None, events_map: dict | None) -> list[dict]:
    """Return a list of typed alerts (most severe first)."""
    events_map = events_map or {}
    alerts: list[dict] = []

    def add(atype, scope, severity, message):
        alerts.append({"type": atype, "scope": scope,
                       "severity": severity, "message": message})

    for _, r in df.iterrows():
        t = r["Ticker"]
        ev = events_map.get(t, {})

        # Breakouts
        if r.get("Breakout"):
            add("פריצה", t, "גבוהה",
                f"{t} פורצת — מעל ממוצעי 50/200, קרוב לשיא, נפח פי {r.get('VolRatio')}")
        # Volume spikes
        if r.get("VolRatio", 0) >= 2:
            add("זינוק נפח", t, "בינונית",
                f"{t} — נפח מסחר פי {r.get('VolRatio')} מהממוצע")
        # Earnings within a week
        dte = ev.get("days_to_earnings")
        if dte is not None and dte <= 7:
            add("דוחות", t, "בינונית",
                f"{t} — דוחות כספיים בעוד {dte} ימים ({ev.get('earnings_date','')})")
        # Analyst actions
        if ev.get("rating_action"):
            sev = "גבוהה" if "הורדת" in str(ev["rating_action"]) else "מידע"
            add("שינוי דירוג", t, sev,
                f"{t} — {ev['rating_action']} ({ev.get('rating_firm','')})")
        # High-risk warning
        if r.get("RiskLevel") == "גבוה" and r.get("Price", 0) < r.get("MA200", 0):
            add("אזהרת סיכון", t, "גבוהה",
                f"{t} — סיכון גבוה ומתחת לממוצע 200")

    # Sector rotation (strongest in, weakest out)
    if sectors and "score" in (sectors[0] if sectors else {}):
        ranked = sorted(sectors, key=lambda s: s["score"], reverse=True)
        top, bot = ranked[0], ranked[-1]
        if top["score"] >= 70:
            add("רוטציית סקטורים", top["sector"], "מידע",
                f"כניסת הון לסקטור {top['sector']} (ציון {top['score']}, חוזק יחסי {top['rs']:+}%)")
        if bot["score"] < 35:
            add("רוטציית סקטורים", bot["sector"], "מידע",
                f"יציאת הון מסקטור {bot['sector']} (ציון {bot['score']}, חוזק יחסי {bot['rs']:+}%)")

    order = {"גבוהה": 0, "בינונית": 1, "מידע": 2}
    alerts.sort(key=lambda a: order.get(a["severity"], 3))
    return alerts
