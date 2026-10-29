# -*- coding: utf-8 -*-
"""The single decision engine — one verdict per stock, used by EVERY screen.

Before this module the app had five independent recommendation paths
(classify, the home ranking, delta.action_for, deepdive.recommendation,
deepdive.investment_decision) with different thresholds, so the same stock
could be "top opportunity" on one page and "stay away" on the next.

A verdict answers three separate questions and never mixes them:
  1. Is this a good company right now?      → quality  (Score V2, unchanged)
  2. Is this a reasonable moment to buy?    → timing   (trend + validated entry rules)
  3. How much can I trust the inputs?       → reliability (completeness/freshness/source)

Actions (for someone who does NOT own the stock):
  buy    🟢 שווה לשקול קנייה
  wait   🟡 להמתין להזדמנות     (always with a concrete condition)
  avoid  🔴 לא עכשיו
  nodata ⚪ אין מספיק מידע אמין  (never guess)
Holder guidance (for someone who DOES own it): hold / caution / review_sell.

Thresholds: quality tiers reuse the existing recommendation scale (68+ = Buy,
55+ = Watch, <45 = Reduce/Avoid). Timing rules are kept ONLY where the
historical study (research/timing_study.py, results in
research/timing_study_results.json) showed a measurable effect — it found
none, see TIMING_EVIDENCE. Pure functions, no I/O except reading that file.
"""
import json
import os
from datetime import date, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_PATH = os.path.join(_HERE, "research", "timing_study_results.json")

# ---------------------------------------------------------------- vocabulary
ACTIONS = {
    "buy":    {"emoji": "🟢", "label": "שווה לשקול קנייה", "short": "לשקול קנייה", "tone": "positive", "rank": 0},
    "wait":   {"emoji": "🟡", "label": "להמתין להזדמנות", "short": "להמתין", "tone": "warning", "rank": 1},
    "avoid":  {"emoji": "🔴", "label": "לא עכשיו", "short": "לא עכשיו", "tone": "negative", "rank": 2},
    "nodata": {"emoji": "⚪", "label": "אין מספיק מידע אמין", "short": "אין מספיק מידע", "tone": "muted", "rank": 3},
}
HOLDER = {
    "hold":        {"emoji": "🟢", "label": "להמשיך להחזיק", "tone": "positive"},
    "caution":     {"emoji": "🟡", "label": "להחזיק ולעקוב מקרוב", "tone": "warning"},
    "review_sell": {"emoji": "🔴", "label": "לבחון מכירה או הקטנה", "tone": "negative"},
    "nodata":      {"emoji": "⚪", "label": "אין מספיק מידע אמין", "tone": "muted"},
}

Q_STRONG, Q_FAIR, Q_WEAK = 68, 55, 45          # existing scale (deepdive.recommendation)
REL_HIGH, REL_MIN = 75, 55                     # reliability bands; below REL_MIN → nodata

# Timing rules — every candidate "wait" rule the app used to apply was tested in
# research/timing_study.py (S&P 500, 2015–2026, 66,625 samples, 3-month excess
# return vs SPY, date-clustered standard errors). None improved outcomes, so none
# gates the verdict. Kept here, documented and inactive, so the decision is
# auditable and a rule can be re-enabled only with new evidence.
TIMING_EVIDENCE = {
    "overbought": {
        "active": False, "test": lambda f, t: t == "up" and (f.get("rsi") or 0) >= 75,
        "reason": lambda f: "המניה עלתה מהר מאוד בשבועות האחרונים",
        "finding": "RSI≥75 in uptrends: +7.5%±1.9 vs +3.5%±0.7 for RSI 50–70 — no underperformance.",
    },
    "poor_reward_risk": {
        "active": False, "test": lambda f, t: f.get("rr") is not None and f["rr"] < 1,
        "reason": lambda f: "המרחק למטה (עד התמיכה) גדול מהמרחק למעלה (עד ההתנגדות)",
        "finding": "R/R<1: +3.8%±0.8 vs R/R≥2: +2.4%±1.2 — not worse.",
    },
    "under_resistance": {
        "active": False,
        "test": lambda f, t: f.get("sr_status") != "breakout" and f.get("dist_res") is not None and f["dist_res"] <= 2,
        "reason": lambda f: "המחיר צמוד לשיא האחרון שלו, שבו היא נעצרה בעבר",
        "finding": "≤2% under resistance: +2.0%±0.8 vs +4.0%±0.8 — weak (≈1.7σ), equal medians.",
    },
    "wait_for_support": {
        "active": False, "test": lambda f, t: f.get("dist_sup") is not None and abs(f["dist_sup"]) > 8,
        "reason": lambda f: "המחיר רחוק מרמת התמיכה",
        "finding": "Far above support: +6.0%±0.9 vs within 3%: +0.9%±0.9 — waiting for support was WORSE.",
    },
}
# Trend IS used, as a risk rule rather than a return forecast: below the 200-day
# average the study shows deeper interim drawdowns (−12.5% vs −11.3%) and a
# worse 10th-percentile outcome (−14.3% vs −13.1%); return differences were not
# significant (and survivorship bias favours losers in that comparison).


# ------------------------------------------------------------------ helpers
def _n(v):
    try:
        if v is None or isinstance(v, bool):
            return None
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _money(v):
    v = _n(v)
    if v is None:
        return "—"
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}"


def _pct(v, plus=True):
    v = _n(v)
    if v is None:
        return "—"
    return f"{v:+.1f}%" if plus else f"{v:.1f}%"


def _age_days(as_of):
    if not as_of:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return (date.today() - datetime.strptime(str(as_of)[:19], fmt).date()).days
        except ValueError:
            continue
    return None


# ----------------------------------------------------------------- features
def features_from_row(r: dict, source: str = "daily") -> dict:
    """Normalise a daily-scan row (results.csv or universe.json) to features."""
    g = lambda k: _n(r.get(k))
    price = g("Price")
    fund = g("ScoreFundamental")
    # Universe rows that were never enriched carry ScoreV2 == technical Score:
    # that is NOT a quality score, so it must not drive a verdict.
    enriched = r.get("Name") is not None or fund is not None
    comp = g("Completeness")
    if comp is None:
        have = {"fundamental": fund is not None, "technical": g("Score") is not None,
                "sector": g("SectorScore") is not None, "news": g("ScoreNews") is not None,
                "risk": g("RiskScore") is not None or g("ScoreRisk") is not None}
        w = {"fundamental": 35, "technical": 25, "sector": 20, "news": 10, "risk": 10}
        comp = sum(w[k] for k, ok in have.items() if ok)
    status = "breakout" if (r.get("Resistance") in (None, "") and g("Support")) else "normal"
    return {
        "ticker": r.get("Ticker"), "name": r.get("Name"),
        "price": price, "ma50": g("MA50"), "ma200": g("MA200"), "rsi": g("RSI14"),
        "ret3m": g("Ret3m"), "dist_high": g("DistFromHigh%"),
        "support": g("Support"), "resistance": g("Resistance"),
        "dist_sup": g("DistSupport%"), "dist_res": g("DistResistance%"), "rr": g("RiskReward"),
        "sr_status": status,
        "quality": g("ScoreV2") if enriched else None, "fundamental": fund,
        "technical": g("Score"), "news": g("ScoreNews"),
        "valuation": g("Valuation"), "sector_score": g("SectorScore"),
        "risk_level": r.get("RiskLevel"), "volatility": g("Volatility"), "max_dd": g("MaxDrawdown"),
        "beta": g("Beta"),
        "rev_growth": g("RevenueGrowth"), "eps_growth": g("EPSGrowth"), "op_margin": g("OperatingMargin"),
        "roic": g("ROIC"), "debt_equity": g("DebtToEquity"), "fwd_pe": g("ForwardPE"), "peg": g("PEG"),
        "target": g("TargetMean"), "target_low": g("TargetLow"), "target_high": g("TargetHigh"),
        "analysts": g("AnalystCount"),
        "sector": r.get("Sector"),
        "days_to_earnings": g("DaysToEarnings"),
        "completeness": comp, "as_of": r.get("Date") or r.get("as_of"), "source": source,
        "fallback": False,
    }


def features_from_report(rep: dict) -> dict:
    """Normalise a live deep-dive report (deepdive.analyze) to features."""
    rm = rep.get("raw_metrics") or {}
    sc = rep.get("scores") or {}
    tech = rep.get("technicals") or {}
    srl = tech.get("sr_levels") or {}
    ma = tech.get("moving_averages") or {}
    rk = rep.get("risk") or {}
    sv = lambda k: _n((sc.get(k) or {}).get("value"))
    base = next((s for s in rep.get("scenarios", []) if s.get("key") == "base"), {}) or {}
    low = next((s for s in rep.get("scenarios", []) if s.get("key") == "bear"), {}) or {}
    high = next((s for s in rep.get("scenarios", []) if s.get("key") == "bull"), {}) or {}
    comp = (rep.get("meta") or {}).get("completeness")
    warns = " ".join(rep.get("quality_warnings") or [])
    return {
        "ticker": rep.get("ticker"), "name": (rep.get("overview") or {}).get("name"),
        "price": _n(rm.get("price")), "ma50": _n(ma.get("ma50")), "ma200": _n(ma.get("ma200")),
        "rsi": _n(rm.get("rsi")), "ret3m": _n(rm.get("ret_3m")),
        "dist_high": _n((tech.get("high_low") or {}).get("dist_from_high")),
        "support": _n(srl.get("support")), "resistance": _n(srl.get("resistance")),
        "dist_sup": _n(srl.get("dist_support_pct")), "dist_res": _n(srl.get("dist_resistance_pct")),
        "rr": _n(srl.get("risk_reward")), "sr_status": srl.get("status") or "normal",
        "quality": sv("final_v2"), "fundamental": sv("fundamental"), "valuation": sv("valuation"),
        "technical": sv("technical"), "news": sv("news"),
        "sector_score": sv("sector"), "risk_level": rk.get("category"),
        "volatility": _n(rk.get("volatility")), "max_dd": _n(rk.get("max_drawdown")), "beta": _n(rk.get("beta")),
        "rev_growth": _n(rm.get("rev_growth")), "eps_growth": _n(rm.get("eps_growth")),
        "op_margin": _n(rm.get("op_margin")), "roic": _n(rm.get("roic")), "debt_equity": _n(rm.get("debt_equity")),
        "fwd_pe": _n(str((rep.get("valuation") or {}).get("forward_pe", "")).replace(",", "")) ,
        "peg": None,
        "target": _n(((base.get("target") or {}).get("price_num"))),
        "target_low": _n(((low.get("target") or {}).get("price_num"))),
        "target_high": _n(((high.get("target") or {}).get("price_num"))),
        "analysts": _n((rep.get("growth") or {}).get("analyst_count")),
        "sector": (rep.get("overview") or {}).get("sector"),
        "days_to_earnings": None, "earnings_date": rm.get("earnings_date"),
        "completeness": (comp * 100) if isinstance(comp, (int, float)) and comp <= 1 else comp,
        "as_of": date.today().strftime("%d/%m/%Y"), "source": "live",
        "fallback": "הסריקה היומית" in warns,
    }


# -------------------------------------------------------------- reliability
def reliability(f: dict) -> dict:
    """ONE data-reliability number (0-100) for the inputs behind a verdict.

    completeness 50 · freshness 25 · critical price fields 15 · source 10.
    Stock data comes from a single provider (Yahoo) with no per-stock cross
    check, so the source points are never awarded: the ceiling is 90.
    """
    comp = _n(f.get("completeness"))
    comp = 0 if comp is None else max(0.0, min(100.0, comp))
    pts = 0.5 * comp
    reasons = []
    if comp >= 90:
        reasons.append("כל רכיבי הניתוח זמינים")
    elif comp >= 65:
        reasons.append("חלק מרכיבי הניתוח חסרים")
    else:
        reasons.append("חסרים נתונים עסקיים מהותיים")
    age = _age_days(f.get("as_of"))
    if age is None or age <= 4:          # daily close data is ≤1 trading day old (+weekend)
        pts += 25
        if age is not None:
            reasons.append("הנתונים עדכניים")
    elif age <= 8:
        pts += 12
        reasons.append(f"הנתונים בני {age} ימים")
    else:
        reasons.append(f"הנתונים ישנים ({age} ימים)")
    crit = [k for k in ("price", "ma200", "support") if f.get(k) is None]
    pts += 15 * (1 - len(crit) / 3)
    if crit:
        reasons.append("חסרות רמות מחיר")
    if f.get("fallback"):
        pts -= 5
        reasons.append("חלק מהנתונים מגיבוי יומי")
    reasons.append("מקור יחיד (Yahoo), ללא אימות צולב למניות")
    score = int(round(max(0, min(100, pts))))
    label = "גבוהה" if score >= REL_HIGH else "בינונית" if score >= REL_MIN else "נמוכה"
    return {"score": score, "label": label, "reasons": reasons,
            "single_source": True, "source_note": "מקור: Yahoo Finance (מקור יחיד)"}


# ------------------------------------------------------------------ reasons
def _trend(f):
    p, m50, m200 = f.get("price"), f.get("ma50"), f.get("ma200")
    if p is None or m200 is None:
        return "unknown"
    if p < m200:
        return "down"
    if m50 is not None and p > m50:
        return "up"
    return "mixed"


def _quality_tier(q):
    if q is None:
        return None
    return "strong" if q >= Q_STRONG else "fair" if q >= Q_FAIR else "weak" if q >= Q_WEAK else "poor"


def _pros(f, trend):
    out = []
    if (f.get("rev_growth") or 0) >= 15:
        out.append(f"המכירות גדלות מהר ({_pct(f['rev_growth'])} בשנה)")
    if (f.get("op_margin") or 0) >= 20:
        out.append(f"רווחית מאוד: מכל 100 דולר מכירות נשארים כ-{f['op_margin']:.0f} דולר רווח תפעולי")
    if (f.get("roic") or 0) >= 15:
        out.append("משתמשת בכסף של המשקיעים ביעילות גבוהה (ROIC גבוה)")
    if f.get("debt_equity") is not None and f["debt_equity"] <= 0.5:
        out.append("חוב נמוך ביחס להון")
    if not out and (f.get("fundamental") or 0) >= 70:
        out.append("הנתונים העסקיים של החברה חזקים")
    if trend == "up":
        out.append("המניה במגמת עלייה (מעל הממוצע של 200 הימים האחרונים)")
    if (f.get("sector_score") or 0) >= 66:
        out.append("הענף שלה חזק כרגע")
    if f.get("risk_level") == "נמוך":
        out.append("מניה יציבה יחסית, עם תנודות מתונות")
    if (f.get("valuation") or 0) >= 65:
        out.append("המחיר סביר ביחס לצמיחה ולרווחים")
    return out


def _cons(f, trend):
    out = []
    if trend == "down":
        out.append("המניה במגמת ירידה (מתחת לממוצע של 200 הימים האחרונים)")
    if f.get("valuation") is not None and f["valuation"] < 40:
        pe = f" (מכפיל עתידי {f['fwd_pe']:.0f})" if f.get("fwd_pe") else ""
        out.append(f"המניה יקרה ביחס לצמיחה ולרווחים{pe}")
    if f.get("risk_level") in ("גבוה", "גבוה מאוד"):
        dd = f" — בשנה האחרונה ירדה עד {abs(f['max_dd']):.0f}% מהשיא" if f.get("max_dd") else ""
        out.append(f"מניה תנודתית{dd}")
    tgt, price = _n(f.get("target")), _n(f.get("price"))
    if tgt and price and tgt < price * 0.98:
        out.append(f"המחיר כבר גבוה ממחיר היעד הממוצע של האנליסטים ({_money(tgt)})")
    if f.get("rev_growth") is not None and f["rev_growth"] < 0:
        out.append(f"המכירות מתכווצות ({_pct(f['rev_growth'])})")
    if f.get("debt_equity") is not None and f["debt_equity"] > 1.5:
        out.append("חוב גבוה ביחס להון")
    if f.get("sector_score") is not None and f["sector_score"] < 40:
        out.append("הענף שלה חלש כרגע")
    if (f.get("rsi") or 0) >= 75:
        out.append("עלתה מהר מאוד לאחרונה, ולכן צפויות תנודות חדות יותר מהרגיל")
    dte = _n(f.get("days_to_earnings"))
    if dte is not None and 0 <= dte <= 7:
        when = "היום" if dte == 0 else "מחר" if dte == 1 else f"בעוד {int(dte)} ימים"
        out.insert(0, f"דוחות כספיים {when} — המחיר עלול לזוז בחדות")
    return out


_DIMS = (("fundamental", "הנתונים העסקיים של החברה"), ("technical", "המצב הטכני של המניה"),
         ("sector_score", "חוזק הענף שלה"), ("news", "החדשות האחרונות עליה"))


def _holding_back(f):
    """The weakest quality dimension (below 55) — what keeps the score down."""
    dims = [(f.get(k), label) for k, label in _DIMS if _n(f.get(k)) is not None]
    dims = [(v, l) for v, l in dims if v < 55]
    if not dims:
        return None
    v, label = min(dims)
    return f"{label} חלשים יחסית ({int(v)} מתוך 100)" if label.endswith("נתונים העסקיים של החברה")         else f"{label} חלש יחסית ({int(v)} מתוך 100)"


def _timing_flags(f, trend):
    """Active, evidence-backed timing problems: [(key, plain reason)]."""
    flags = []
    for key, rule in TIMING_EVIDENCE.items():
        try:
            if rule["active"] and rule["test"](f, trend):
                flags.append((key, rule["reason"](f)))
        except Exception:
            continue
    return flags


# ------------------------------------------------------------------ verdict
def decide(f: dict) -> dict:
    """The verdict for one stock (see module docstring)."""
    rel = reliability(f)
    trend = _trend(f)
    q = _n(f.get("quality"))
    tier = _quality_tier(q)
    pros, cons = _pros(f, trend), _cons(f, trend)
    flags = _timing_flags(f, trend)
    very_high_risk = f.get("risk_level") == "גבוה מאוד"
    sup, res, price = f.get("support"), f.get("resistance"), f.get("price")

    conditions, why = [], ""
    if tier is None or rel["score"] < REL_MIN or price is None:
        action = "nodata"
        why = ("חסרים נתונים עסקיים מהותיים, ולכן המערכת לא נותנת המלצה. "
               "אפשר לראות את התמונה הטכנית בניתוח המקצועי.")
    elif tier == "poor" or (trend == "down" and tier != "strong") or (very_high_risk and tier != "strong"):
        action = "avoid"
        if tier == "poor":
            weak = next((c for c in cons if not c.startswith("דוחות")), None)
            why = "הנתונים הנוכחיים חלשים מכדי להצדיק השקעה" + (f": {weak}." if weak else ".")
        elif trend == "down":
            why = "המניה במגמת ירידה והחברה לא מספיק חזקה כדי לפצות על כך."
        else:
            why = "הסיכון גבוה מאוד ביחס לאיכות שהחברה מציגה כרגע."
            conditions.append("ירידה בתנודתיות של המניה, או שיפור משמעותי בנתונים העסקיים")
        if trend == "down" and f.get("ma200"):
            conditions.append(f"חזרה מעל {_money(f['ma200'])} (הממוצע של 200 יום) תשפר את התמונה")
        if tier in ("poor", "weak"):
            conditions.append("שיפור בנתונים העסקיים (צמיחה ורווחיות)")
    elif tier == "strong" and trend != "down" and not flags and not very_high_risk:
        action = "buy"
        lead = next((p for p in pros if "מגמת" not in p), None)
        why = (f"חברה חזקה — {lead}. " if lead else "חברה חזקה. ") + (
            "המניה במגמת עלייה." if trend == "up" else "המניה יציבה מעל הממוצע ארוך הטווח.")
        if sup:
            conditions.append(f"ירידה מתחת ל-{_money(sup)} (רמת התמיכה) תבטל את ההמלצה")
    else:
        action = "wait"
        if tier == "strong" and trend == "down":
            why = "חברה חזקה, אבל המניה במגמת ירידה. עדיף לחכות להתייצבות."
            if f.get("ma200"):
                conditions.append(f"חזרה מעל {_money(f['ma200'])} (הממוצע של 200 יום)")
        elif tier == "strong" and flags:
            why = "חברה חזקה, אבל זה לא רגע טוב להיכנס: " + flags[0][1] + "."
            if sup and price and sup < price:
                conditions.append(f"מחיר כניסה נוח יותר: קרוב ל-{_money(sup)} (רמת התמיכה)")
            for _, r in flags[1:2]:
                conditions.append(r)
        elif tier == "strong":
            why = "חברה חזקה, אבל רמת הסיכון גבוהה מאוד."
            conditions.append("ירידה בתנודתיות, או כניסה בסכום קטן בלבד")
        else:
            weak = next((c for c in cons if not c.startswith("דוחות")), None) or _holding_back(f)
            why = (f"חברה סבירה (ציון {int(q)} מתוך 100), אבל עוד לא מספיק חזקה"
                   + (f": {weak}." if weak else "."))
            conditions.append(f"שיפור בציון האיכות מעל {Q_STRONG}")
            if sup and price and sup < price:
                conditions.append(f"או ירידה לאזור {_money(sup)} (רמת התמיכה)")

    # Holder guidance
    if action == "nodata":
        holder = "nodata"
        holder_why = "אין מספיק נתונים אמינים כדי לתת הנחיה."
    elif tier == "poor" or (trend == "down" and tier in ("weak", "poor")) or (
            f.get("sr_status") == "breakdown" and tier != "strong"):
        holder = "review_sell"
        holder_why = "התמונה נחלשה: כדאי לבדוק אם הסיבה שבגללה קנית עדיין קיימת."
    elif trend == "down" or tier == "weak" or very_high_risk or flags:
        holder = "caution"
        holder_why = ("המניה מראה סימני חולשה, כדאי לעקוב." if trend == "down" or tier == "weak"
                      else "אין סיבה למכור, אבל כדאי לא להגדיל את הפוזיציה כרגע.")
        if sup:
            holder_why += f" ירידה מתחת ל-{_money(sup)} היא סימן אזהרה."
    else:
        holder = "hold"
        holder_why = "התמונה תקינה. אין סיבה מהנתונים לשנות את ההחזקה."

    target = _n(f.get("target"))
    upside = round((target / price - 1) * 100, 1) if target and price else None
    downside = _n(f.get("dist_sup"))

    a = ACTIONS[action]
    return {
        "ticker": f.get("ticker"), "name": f.get("name"),
        "action": action, **{k: a[k] for k in ("emoji", "label", "short", "tone", "rank")},
        "why": why, "pros": pros[:3], "cons": (([r for _, r in flags]) + cons)[:3],
        "conditions": conditions[:2],
        "holder": holder, "holder_label": HOLDER[holder]["label"], "holder_emoji": HOLDER[holder]["emoji"],
        "holder_tone": HOLDER[holder]["tone"], "holder_why": holder_why,
        "quality": q, "quality_tier": tier, "trend": trend, "timing_flags": [k for k, _ in flags],
        "levels": {"price": price, "target": target, "upside": upside,
                   "target_low": _n(f.get("target_low")), "target_high": _n(f.get("target_high")),
                   "analysts": _n(f.get("analysts")),
                   "support": sup, "downside": downside, "resistance": res,
                   "dist_res": _n(f.get("dist_res"))},
        "reliability": rel, "evidence": evidence_for(f, trend),
        "as_of": f.get("as_of"), "source": f.get("source"),
    }


def verdict_for_row(r: dict, source: str = "daily") -> dict:
    return decide(features_from_row(r, source))


_COMPAT_GROUP = {"buy": "positive", "avoid": "avoid"}
_COMPAT_COLOR = {"positive": "#1b7f3b", "watch": "#b8860b", "avoid": "#b3333b"}


def classify_compat(row) -> dict:
    """The verdict in the shape of ranking_engine.interpret.classify(), so the
    e-mail/HTML reports speak with the same voice as the app."""
    r = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    v = verdict_for_row(r)
    g = _COMPAT_GROUP.get(v["action"], "watch")
    return {"group": g, "emoji": v["emoji"], "label": v["short"], "color": _COMPAT_COLOR[g],
            "summary": v["why"], "detail": " · ".join(v["pros"] + v["cons"]), "verdict": v}


def verdict_for_report(rep: dict) -> dict:
    return decide(features_from_report(rep))


# ----------------------------------------------------------------- evidence
_EVIDENCE_CACHE = {}


def _load_evidence():
    if "d" not in _EVIDENCE_CACHE:
        try:
            with open(EVIDENCE_PATH, encoding="utf-8") as fh:
                _EVIDENCE_CACHE["d"] = json.load(fh)
        except Exception:
            _EVIDENCE_CACHE["d"] = None
    return _EVIDENCE_CACHE["d"]


def evidence_for(f: dict, trend: str | None = None) -> dict | None:
    """Historical base rate for the stock's current technical setup, or None.
    Shown only when the bucket has a large sample (see research/)."""
    ev = _load_evidence()
    if not ev or "setups" not in ev:
        return None
    trend = trend or _trend(f)
    rsi = _n(f.get("rsi"))
    if trend == "unknown" or rsi is None:
        return None
    band = "lt50" if rsi < 50 else "50_70" if rsi < 70 else "ge70"
    key = f"{trend}|{band}"
    s = ev["setups"].get(key)
    if not s or s.get("n", 0) < 300:
        return None
    return {**s, "key": key, "period": f"{ev['meta']['first_date'][:4]}–{ev['meta']['last_date'][:4]}",
            "universe": "S&P 500"}
