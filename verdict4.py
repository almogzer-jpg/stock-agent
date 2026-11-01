# -*- coding: utf-8 -*-
"""Four-dimension decision engine (owner approval 01/11/2026, version A).

Four separate answers and ONE decision derived from them by an explicit table
(DECISION_ENGINE_PROPOSAL.md):

  1. Company quality       business data only: profitability, growth, cash flow,
                           balance sheet, stability. No price, no multiples, no momentum.
  2. Price attractiveness  several sources, never one: peers in the same industry,
                           the company's own P/E history, the growth-adjusted multiple
                           (PEG) and the analyst consensus. Above the consensus target the
                           target never supports "attractive". Another source may, and
                           then it is named explicitly.
  3. Momentum and timing   trend vs the 50/200-day averages, technical score, sector
                           momentum. The research (research/README.md) shows these describe
                           trend and risk, not expected return, so they gate only through
                           the trend rule.
  4. Risk                  volatility / drawdown / beta level, earnings date, data reliability.

Runs in SHADOW mode (shadow.py): computed and logged every day, never displayed,
until the owner approves the switch on measured outcomes. Pure functions.
"""
import statistics

from verdict import ACTIONS, HOLDER, Q_STRONG, Q_FAIR, Q_WEAK, REL_HIGH, REL_MIN, _n, _money, _age_days

FINANCIAL = ("Financial Services",)
MIN_PEERS = 6

Q_LABELS = {"strong": ("חברה חזקה", "positive"), "fair": ("חברה סבירה", "warning"),
            "weak": ("חברה חלשה", "negative"), "poor": ("חברה חלשה מאוד", "negative")}
P_LABELS = {"attractive": ("מחיר אטרקטיבי", "positive"), "fair": ("מחיר הוגן", "positive"),
            "full": ("מחיר מלא", "warning"), "expensive": ("מחיר גבוה", "negative")}
T_LABELS = {"positive": ("מגמה חיובית", "positive"), "mixed": ("מגמה מעורבת", "warning"),
            "negative": ("מגמה שלילית", "negative"), "unknown": ("אין מספיק מידע", "muted")}
R_TONES = {"נמוך": "positive", "בינוני": "warning", "גבוה": "negative", "גבוה מאוד": "negative"}


# ------------------------------------------------------------------ helpers
def _grade(v, steps, floor):
    """Points for a higher-is-better metric: the first (threshold, points) met, else floor."""
    for thr, pts in steps:
        if v >= thr:
            return pts
    return floor


def _grade_low(v, steps, ceiling_pts):
    """Points for a lower-is-better metric: the first (threshold, points) with v <= threshold."""
    for thr, pts in steps:
        if v <= thr:
            return pts
    return ceiling_pts


def _valid(seq, positive=False):
    out = []
    for x in seq or []:
        x = _n(x)
        if x is None:
            break                       # stop at the first gap: history must be consecutive
        if positive and x <= 0:
            continue
        out.append(x)
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


# ------------------------------------------------------------- 1. quality
def quality(p: dict) -> dict:
    """Business-only quality, 0-100, from the profile. None when the core is missing."""
    p = p or {}
    fin = p.get("sector") in FINANCIAL
    pil, good, bad = {}, [], []

    om, roe, roa = _n(p.get("op_margin")), _n(p.get("roe")), _n(p.get("roa"))
    if (_n(p.get("book_value")) or 0) <= 0:
        roe = None                      # negative equity (buybacks) makes ROE meaningless
    prof = []
    if om is not None and not fin:
        prof.append(_grade(om, [(25, 90), (15, 75), (8, 55), (0, 35)], 10))
        if om >= 25:
            good.append(f"רווחיות גבוהה מאוד (רווח תפעולי {om:.0f}% מהמכירות)")
        elif om < 5:
            bad.append(f"רווחיות נמוכה (רווח תפעולי {om:.0f}% מהמכירות)")
    if roe is not None:
        prof.append(_grade(roe, [(20, 90), (12, 70), (6, 50), (0, 30)], 10))
        if roe >= 20:
            good.append(f"תשואה גבוהה על ההון ({roe:.0f}%)")
    elif roa is not None:
        steps = [(1.2, 85), (0.8, 65), (0.4, 45), (0, 30)] if fin else [(10, 90), (5, 70), (2, 50), (0, 30)]
        prof.append(_grade(roa, steps, 10))
    if prof:
        pil["profitability"] = _mean(prof)

    rev_hist = _valid(p.get("rev_hist"))
    gro = []
    rg, eg = _n(p.get("rev_growth")), _n(p.get("eps_growth"))
    if rg is not None:
        gro.append(_grade(rg, [(15, 90), (8, 75), (3, 60), (0, 45), (-5, 30)], 15))
    cagr = None
    if len(rev_hist) >= 4 and rev_hist[3] > 0:
        cagr = ((rev_hist[0] / rev_hist[3]) ** (1 / 3) - 1) * 100
        gro.append(_grade(cagr, [(15, 90), (8, 75), (3, 60), (0, 45), (-5, 30)], 15))
    if eg is not None:
        gro.append(_grade(eg, [(20, 90), (10, 75), (0, 55), (-10, 35)], 15))
    if gro:
        pil["growth"] = _mean(gro)
        if rg is not None and rg >= 15:
            good.append(f"המכירות גדלות מהר ({rg:+.0f}% בשנה)")
        elif cagr is not None and cagr >= 8:
            good.append(f"צמיחה עקבית במכירות ({cagr:+.0f}% בשנה בממוצע ב-3 שנים)")
        if rg is not None and rg < 0:
            bad.append(f"המכירות יורדות ({rg:.0f}% בשנה)")

    fcf, rev = _n(p.get("fcf")), _n(p.get("revenue"))
    if not fin and fcf is not None and rev:
        m = fcf / rev * 100
        pil["cash"] = _grade(m, [(20, 90), (10, 75), (5, 60), (0, 40)], 15)
        if m >= 20:
            good.append(f"מייצרת הרבה מזומנים ({m:.0f}% מהמכירות)")
        elif m < 0:
            bad.append("תזרים המזומנים החופשי שלילי")

    if not fin:
        debt, cash, ebitda = _n(p.get("total_debt")), _n(p.get("total_cash")), _n(p.get("ebitda"))
        if debt is not None and ebitda is not None:
            nd = debt - (cash or 0)
            if ebitda > 0:
                lev = nd / ebitda
                pil["balance"] = _grade_low(lev, [(0, 95), (1, 85), (2, 70), (3, 50), (4, 35)], 15)
                if lev <= 1:
                    good.append("חוב נמוך ביחס לרווח")
                elif lev > 3:
                    bad.append(f"חוב גבוה (פי {lev:.1f} מהרווח התפעולי השנתי)")
            elif nd > 0:
                pil["balance"] = 15
                bad.append("יש חוב נטו בלי רווח תפעולי שמכסה אותו")
        elif _n(p.get("debt_equity")) is not None:
            pil["balance"] = _grade_low(p["debt_equity"], [(0.5, 85), (1, 70), (2, 50), (3, 30)], 15)

    stab = []
    if len(rev_hist) >= 3:
        ups = sum(1 for a, b in zip(rev_hist[:3], rev_hist[1:4]) if a > b)
        stab.append({3: 90, 2: 65, 1: 40, 0: 20}[min(ups, 3)])
        if ups >= 3 and len(rev_hist) >= 4:
            good.append("ההכנסות עלו בכל אחת מ-3 השנים האחרונות")
    omh = _valid(p.get("op_margin_hist"))
    if not fin and len(omh) >= 3:
        sd = statistics.pstdev(omh[:4])
        stab.append(_grade_low(sd, [(3, 85), (6, 65), (10, 45)], 25))
        if sd > 10:
            bad.append("הרווחיות לא יציבה משנה לשנה")
    eps_h = _valid(p.get("eps_hist"))
    if len(eps_h) >= 3:
        stab.append(round(85 * sum(1 for e in eps_h if e > 0) / len(eps_h)))
    fcf_h = _valid(p.get("fcf_hist"))
    if not fin and len(fcf_h) >= 3:
        stab.append(round(85 * sum(1 for e in fcf_h if e > 0) / len(fcf_h)))
    if stab:
        pil["stability"] = _mean(stab)

    w = {"profitability": 0.30, "growth": 0.25, "cash": 0.15, "balance": 0.15, "stability": 0.15}
    if "profitability" not in pil or "growth" not in pil or len(pil) < 3:
        return {"score": None, "tier": None, "label": "אין מספיק מידע", "tone": "muted",
                "pillars": pil, "completeness": round(sum(w[k] for k in pil), 2), "good": good, "bad": bad,
                "basis": "חסרים נתונים עסקיים בסיסיים (רווחיות או צמיחה)"}
    tot = sum(w[k] for k in pil)
    score = round(sum(v * w[k] for k, v in pil.items()) / tot)
    tier = "strong" if score >= Q_STRONG else "fair" if score >= Q_FAIR else "weak" if score >= Q_WEAK else "poor"
    label, tone = Q_LABELS[tier]
    return {"score": score, "tier": tier, "label": label, "tone": tone,
            "pillars": {k: round(v) for k, v in pil.items()}, "completeness": round(tot, 2),
            "good": good, "bad": bad,
            "basis": f"ציון עסקי {score} מתוך 100 (רווחיות, צמיחה, תזרים, חוב ויציבות)"}


# ------------------------------------------------------------ 2. price
def context(profiles: dict) -> dict:
    """Universe-wide reference values: peer multiples per industry/sector and the
    median analyst upside (analysts are optimistic on average, so a stock's gap is
    read against the typical gap rather than against zero)."""
    groups, ups = {}, []
    for t, p in (profiles or {}).items():
        for level in ("industry", "sector"):
            g = p.get(level)
            if not g:
                continue
            d = groups.setdefault((level, g), {"fwd_pe": {}, "ev_ebitda": {}})
            fpe, eve = _n(p.get("fwd_pe")), _n(p.get("ev_ebitda"))
            if fpe is not None and 0 < fpe < 200:
                d["fwd_pe"][t] = fpe
            if eve is not None and 0 < eve < 100 and p.get("sector") not in FINANCIAL:
                d["ev_ebitda"][t] = eve
        tgt, px, n = _n(p.get("target_mean")), _n(p.get("price")), _n(p.get("analysts"))
        if tgt and px and (n or 0) >= 5:
            ups.append((tgt / px - 1) * 100)
    return {"groups": groups, "median_upside": statistics.median(ups) if ups else 0.0}


def _peers(ticker, p, ctx):
    """Percentile of the stock's multiples among its industry (else sector) peers."""
    for level in ("industry", "sector"):
        g = (ctx.get("groups") or {}).get((level, p.get(level)))
        if not g:
            continue
        pcts, n = [], 0
        for key in ("fwd_pe", "ev_ebitda"):
            own = g[key].get(ticker)
            others = [v for t, v in g[key].items() if t != ticker]
            if own is None or len(others) < MIN_PEERS:
                continue
            pcts.append(100 * sum(1 for v in others if v < own) / len(others))
            n = max(n, len(others))
        if pcts:
            return {"level": level, "group": p.get(level), "n": n, "pct": _mean(pcts)}
    return None


def price(ticker: str, p: dict, ctx: dict) -> dict:
    """Price attractiveness from every available source, each with its own reason."""
    p, comps = p or {}, []
    px = _n(p.get("price"))

    peer = _peers(ticker, p, ctx or {})
    if peer:
        cheaper = 100 - peer["pct"]
        where = "בענף" if peer["level"] == "industry" else "בסקטור"
        if cheaper >= 99.5 or peer["pct"] >= 99.5:
            txt = f"{'זולה' if cheaper >= 50 else 'יקרה'} מכל {peer['n']} החברות {where} לפי מכפילי רווח"
        else:
            txt = (f"זולה מ-{cheaper:.0f}% מ-{peer['n']} החברות {where} לפי מכפילי רווח" if cheaper >= 50
                   else f"יקרה מ-{peer['pct']:.0f}% מ-{peer['n']} החברות {where} לפי מכפילי רווח")
        comps.append({"key": "peers", "score": round(cheaper), "text": txt})

    eps = _n(p.get("trailing_eps"))
    hist = [x for x in (_n(v) for v in (p.get("pe_hist") or [])) if x is not None and 0 < x < 300]
    if px and eps and eps > 0 and len(hist) >= 3:
        now, med = px / eps, statistics.median(hist)
        ratio = now / med
        sc = max(5, min(95, round(50 + (1 - ratio) * 100)))
        diff = abs(ratio - 1) * 100
        txt = (f"מכפיל הרווח ({now:.0f}) נמוך ב-{diff:.0f}% מהרגיל שלה ב-{len(hist)} השנים האחרונות ({med:.0f})"
               if ratio < 1 else
               f"מכפיל הרווח ({now:.0f}) גבוה ב-{diff:.0f}% מהרגיל שלה ב-{len(hist)} השנים האחרונות ({med:.0f})")
        comps.append({"key": "history", "score": sc, "text": txt, "median_pe": med, "eps": eps})

    peg = _n(p.get("peg"))
    if peg is not None and peg > 0:
        sc = _grade_low(peg, [(1, 85), (1.5, 68), (2, 52), (3, 35)], 20)
        comps.append({"key": "growth", "score": sc,
                      "text": f"מכפיל ביחס לצמיחה הצפויה (PEG) {peg:.1f}"})

    tgt, n = _n(p.get("target_mean")), _n(p.get("analysts"))
    up = None
    if tgt and px and (n or 0) >= 5:
        up = (tgt / px - 1) * 100
        sc = max(0, min(100, round(50 + 2.5 * (up - (ctx or {}).get("median_upside", 0.0)))))
        if up < 0:
            sc = min(sc, 35)            # above the consensus target: never support attractiveness
        side = "מעל " if up < 0 else "מתחת ל"
        comps.append({"key": "analysts", "score": sc, "target": tgt, "upside": round(up, 1),
                      "text": f"המחיר {abs(up):.0f}% {side}יעד הממוצע של {int(n)} אנליסטים ({_money(tgt)})"})

    w = {"peers": 0.30, "history": 0.25, "growth": 0.20, "analysts": 0.25}
    if len(comps) < 2:
        return {"score": None, "label": None, "title": "אין מספיק מידע", "tone": "muted",
                "components": comps, "upside": up, "basis": "פחות משני מקורות תמחור זמינים"}

    def combine(cs):
        tot = sum(w[c["key"]] for c in cs)
        return round(sum(c["score"] * w[c["key"]] for c in cs) / tot)

    def label_of(s):
        return "attractive" if s >= 65 else "fair" if s >= 50 else "full" if s >= 35 else "expensive"

    score = combine(comps)
    label = label_of(score)
    support = [c for c in comps if c["score"] >= 60 and c["key"] != "analysts"] + \
              [c for c in comps if c["score"] >= 60 and c["key"] == "analysts"]
    if label == "attractive" and len(support) < 2:
        label = "fair"                  # "attractive" needs at least two agreeing sources
    justification = None
    if up is not None and up < 0 and label in ("attractive", "fair"):
        others = [c for c in comps if c["key"] != "analysts"]
        alt = label_of(combine(others)) if len(others) >= 2 else "full"
        if alt in ("attractive", "fair"):
            label = alt if alt != "attractive" or len([c for c in others if c["score"] >= 60]) >= 2 else "fair"
            best = sorted((c for c in others if c["score"] >= 50), key=lambda c: -c["score"])[:2]
            justification = ("המחיר מעל יעד האנליסטים, ולכן ההערכה לא נשענת עליו. "
                             + ("היא נשענת על: " + " וגם ".join(c["text"] for c in best) + "." if best else ""))
        else:
            label = "full"
    title, tone = P_LABELS[label]
    return {"score": score, "label": label, "title": title, "tone": tone, "components": comps,
            "upside": None if up is None else round(up, 1), "justification": justification,
            "basis": " · ".join(c["text"] for c in comps)}


# ----------------------------------------------------------- 3. timing
def timing(row: dict, sector_score=None) -> dict:
    g = lambda k: _n((row or {}).get(k))
    px, m50, m200, rsi, tech = g("Price"), g("MA50"), g("MA200"), g("RSI14"), g("Score")
    if px is None or m200 is None:
        trend = "unknown"
    elif px < m200:
        trend = "down"
    elif m50 is not None and px > m50:
        trend = "up"
    else:
        trend = "mixed"
    label = {"down": "negative", "unknown": "unknown"}.get(trend) or (
        "positive" if trend == "up" and (tech is None or tech >= 50) else "mixed")
    bits = []
    if trend == "up":
        bits.append("מעל הממוצע של 50 ו-200 יום")
    elif trend == "mixed":
        bits.append("מעל הממוצע של 200 יום, מתחת לממוצע של 50")
    elif trend == "down":
        bits.append("מתחת לממוצע של 200 יום")
    if tech is not None:
        bits.append(f"מומנטום {int(tech)} מתוך 100")
    if sector_score is not None:
        bits.append(f"מגמת הסקטור {int(sector_score)} מתוך 100")
    stretched = rsi is not None and rsi >= 75
    title, tone = T_LABELS[label]
    return {"trend": trend, "label": label, "title": title, "tone": tone, "technical": tech,
            "sector": sector_score, "stretched": stretched,
            "basis": " · ".join(bits) + (" · עלתה מהר בשבועות האחרונים (תנודתיות גבוהה יותר)" if stretched else "")}


# ------------------------------------------------------------- 4. risk
def reliability4(row, p, q, pr) -> dict:
    """Data reliability for the four-dimension verdict (single source: ceiling 90)."""
    pts = 45 * (q.get("completeness") or 0)
    pts += 20 * min(len(pr.get("components") or []), 4) / 4
    age = _age_days((row or {}).get("Date") or (row or {}).get("as_of"))
    pts += 15 if age is None or age <= 4 else 7 if age <= 8 else 0
    p_age = _age_days((p or {}).get("_date"))
    pts += 10 if p_age is not None and p_age <= 10 else 0
    score = int(round(max(0, min(90, pts))))
    return {"score": score, "label": "גבוהה" if score >= REL_HIGH else "בינונית" if score >= REL_MIN else "נמוכה",
            "source_note": "מקור: Yahoo Finance (מקור יחיד)"}


def risk(row: dict, rel: dict, days_to_earnings=None) -> dict:
    g = lambda k: _n((row or {}).get(k))
    lvl = (row or {}).get("RiskLevel") or None
    bits = []
    if g("Volatility") is not None:
        bits.append(f"תנודתיות {g('Volatility'):.0f}% בשנה")
    if g("MaxDrawdown") is not None:
        bits.append(f"ירידה מקסימלית {g('MaxDrawdown'):.0f}%")
    if g("Beta") is not None:
        bits.append(f"בטא {g('Beta'):.2f}")
    soon = days_to_earnings is not None and 0 <= days_to_earnings <= 7
    if soon:
        bits.append(f"דוחות בעוד {int(days_to_earnings)} ימים")
    bits.append(f"אמינות הנתונים {rel['label']}")
    return {"level": lvl, "title": f"סיכון {lvl}" if lvl else "אין מספיק מידע",
            "tone": R_TONES.get(lvl, "muted"), "very_high": lvl == "גבוה מאוד",
            "earnings_soon": soon, "basis": " · ".join(bits)}


# ------------------------------------------------------------ decision
def decide(ticker: str, row: dict, profile: dict, ctx: dict, sector_score=None,
           days_to_earnings=None) -> dict:
    q = quality(profile)
    pr = price(ticker, profile, ctx)
    tm = timing(row, sector_score)
    rel = reliability4(row, profile, q, pr)
    rk = risk(row, rel, days_to_earnings)
    tier, plabel, trend = q["tier"], pr["label"], tm["trend"]
    px = _n((row or {}).get("Price")) or _n((profile or {}).get("price"))
    m200 = _n((row or {}).get("MA200"))
    conditions, reason = [], None
    strength = q["good"][0] if q["good"] else None
    weakness = q["bad"][0] if q["bad"] else None

    if tier is None or rel["score"] < REL_MIN or px is None:
        action, reason = "nodata", "no_data"
        why = "חסרים נתונים עסקיים או נתוני מחיר מהותיים, ולכן המערכת לא נותנת המלצה."
    elif tier == "poor":
        action, reason = "avoid", "weak_business"
        why = "הנתונים העסקיים חלשים מכדי להצדיק השקעה" + (f": {weakness}." if weakness else ".")
        conditions.append("שיפור בנתונים העסקיים (צמיחה ורווחיות)")
    elif trend == "down" and tier != "strong":
        action, reason = "avoid", "downtrend_not_strong"
        why = "המניה במגמת ירידה, והחברה לא מספיק חזקה כדי לפצות על כך."
        if m200:
            conditions.append(f"חזרה מעל {_money(m200)} (הממוצע של 200 יום)")
    elif rk["very_high"] and tier != "strong":
        action, reason = "avoid", "risk_not_strong"
        why = "הסיכון גבוה מאוד ביחס לאיכות שהחברה מציגה."
    elif tier == "strong" and trend == "down":
        action, reason = "wait", "strong_downtrend"
        why = "חברה חזקה, אבל המניה במגמת ירידה. עדיף לחכות להתייצבות."
        if m200:
            conditions.append(f"חזרה מעל {_money(m200)} (הממוצע של 200 יום)")
    elif tier == "strong" and rk["very_high"]:
        action, reason = "wait", "strong_very_high_risk"
        why = "חברה חזקה, אבל רמת הסיכון של המניה גבוהה מאוד."
        conditions.append("ירידה בתנודתיות, או כניסה בסכום קטן בלבד")
    elif tier == "strong" and plabel is None:
        action, reason = "wait", "strong_no_price"
        why = "חברה חזקה, אבל אין מספיק מידע כדי לקבוע אם המחיר סביר."
    elif tier == "strong" and plabel in ("full", "expensive"):
        action, reason = "wait", "strong_full_price"
        why = (f"חברה חזקה, אבל {'המחיר כבר מלא' if plabel == 'full' else 'המחיר גבוה'}: "
               f"{_price_reason(pr)}.{_counterpoint(pr)} למי שמחזיק אין סיבה למכור. "
               "לכסף חדש עדיף לחכות למחיר טוב יותר.")
        conditions += _entry_conditions(pr, px)
    elif tier == "strong":
        action, reason = "buy", "strong_good_price"
        why = (f"חברה חזקה{' (' + strength + ')' if strength else ''} ב{P_LABELS[plabel][0]}: "
               f"{_price_reason(pr)}. " + ("המגמה תומכת." if trend == "up" else "המגמה לא נגדה."))
        sup = _n((row or {}).get("Support"))
        if sup:
            conditions.append(f"ירידה מתחת ל-{_money(sup)} (רמת התמיכה) מחייבת בדיקה מחדש")
    else:
        action, reason = "wait", "not_strong_enough"
        why = (f"{q['label']} (ציון עסקי {q['score']} מתוך 100), עוד לא מספיק חזקה"
               + (f": {weakness}." if weakness else "."))
        conditions.append(f"שיפור בנתונים העסקיים לציון {Q_STRONG} ומעלה")
    if pr.get("justification") and action != "nodata":
        why += " " + pr["justification"]
    if rk["earnings_soon"] and action == "buy":
        why += " הדוחות הקרובים עלולים להזיז את המחיר בחדות."

    # Holder guidance: a full price is a reason not to add, never a reason to sell a strong company.
    if action == "nodata":
        holder, holder_why = "nodata", "אין מספיק נתונים אמינים כדי לתת הנחיה."
    elif tier == "poor" or (trend == "down" and tier in ("weak", "poor")):
        holder, holder_why = "review_sell", "התמונה העסקית או המגמה נחלשו: כדאי לבדוק אם הסיבה שבגללה קנית עדיין קיימת."
    elif trend == "down" or tier == "weak" or rk["very_high"]:
        holder, holder_why = "caution", "יש סימני חולשה או סיכון גבוה, כדאי לעקוב מקרוב."
    elif tier == "strong" and plabel in ("full", "expensive"):
        holder, holder_why = "hold", "חברה חזקה במחיר מלא: אין סיבה למכור, אבל גם לא להגדיל עכשיו."
    else:
        holder, holder_why = "hold", "התמונה תקינה. אין סיבה מהנתונים לשנות את ההחזקה."

    a = ACTIONS[action]
    return {
        "ticker": ticker, "engine": "four_dimensions_v1",
        "action": action, **{k: a[k] for k in ("emoji", "label", "short", "tone", "rank")},
        "reason": reason, "why": why, "conditions": conditions[:2],
        "holder": holder, "holder_label": HOLDER[holder]["label"], "holder_why": holder_why,
        "dimensions": {
            "quality": {"label": q["label"], "tone": q["tone"], "score": q["score"], "tier": tier,
                        "basis": q["basis"], "pillars": q["pillars"], "good": q["good"][:3], "bad": q["bad"][:3]},
            "price": {"label": pr["title"], "tone": pr["tone"], "score": pr["score"], "key": plabel,
                      "basis": pr["basis"], "upside": pr.get("upside"), "justification": pr.get("justification"),
                      "components": [{k: c[k] for k in ("key", "score", "text")} for c in pr["components"]]},
            "timing": {"label": tm["title"], "tone": tm["tone"], "key": tm["label"], "trend": trend,
                       "basis": tm["basis"], "stretched": tm["stretched"]},
            "risk": {"label": rk["title"], "tone": rk["tone"], "level": rk["level"], "basis": rk["basis"],
                     "earnings_soon": rk["earnings_soon"]},
        },
        "reliability": rel, "price": px,
    }


def _price_reason(pr):
    comps = sorted(pr.get("components") or [], key=lambda c: c["score"],
                   reverse=pr.get("label") in ("attractive", "fair"))
    return " וגם ".join(c["text"] for c in comps[:2])


def _counterpoint(pr):
    """For a full / high price, the source that points the other way, so the answer stays balanced."""
    pro = sorted((c for c in pr.get("components") or [] if c["score"] >= 60), key=lambda c: -c["score"])
    return f" מנגד: {pro[0]['text']}." if pro else ""


def _entry_conditions(pr, px=None):
    """Concrete entry prices, only those below today's price (otherwise they are not a condition)."""
    comps = {c["key"]: c for c in pr.get("components") or []}
    out = []
    a, h = comps.get("analysts"), comps.get("history")
    if a and a.get("target") and (px is None or a["target"] / 1.10 < px):
        out.append(f"מחיר של כ-{_money(a['target'] / 1.10)} ומטה (מרווח של 10% עד יעד האנליסטים)")
    if h and h.get("median_pe") and h.get("eps") and (px is None or h["median_pe"] * h["eps"] < px):
        out.append(("או " if out else "") + f"מכפיל רווח שחוזר לרגיל שלה (מחיר של כ-{_money(h['median_pe'] * h['eps'])})")
    return out or ["ירידה במחיר, או שיפור בתמחור ביחס לחברות דומות"]


def consistency(v: dict) -> list:
    """Rules the final answer must never break. Returns the violations (empty = consistent)."""
    d, bad = v["dimensions"], []
    if v["action"] == "buy":
        if d["quality"]["tier"] != "strong":
            bad.append("buy without a strong company")
        if d["price"]["key"] not in ("attractive", "fair"):
            bad.append("buy without a reasonable price")
        if d["timing"]["trend"] == "down":
            bad.append("buy in a downtrend")
        if d["risk"]["level"] == "גבוה מאוד":
            bad.append("buy at very high risk")
    up = d["price"].get("upside")
    if up is not None and up < 0 and d["price"]["key"] in ("attractive", "fair") and not d["price"].get("justification"):
        bad.append("price called reasonable above the analyst target without another stated reason")
    if v["action"] == "wait" and not v["conditions"] and v["reason"] not in ("strong_no_price",):
        bad.append("wait without a condition")
    return bad
