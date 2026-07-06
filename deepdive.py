# -*- coding: utf-8 -*-
"""Company Deep Dive (Phase 18) — full per-ticker investment analysis.

On-demand (the user types any ticker), so unlike the rest of the dashboard this
makes LIVE yfinance calls (cached per-ticker at the UI layer). It REUSES the
existing engines (score / risk / composite / decisions / trust / fundamentals /
news) without changing their logic, and assembles a structured Hebrew report.

Anti-hallucination rules (hard):
  • Every value is a real yfinance field or computed from real data; missing →
    NA ("אין נתון זמין"). Never invent numbers or fake precision.
  • Bull/base/bear, pros/cons, and the final opinion are RULE-BASED templates
    filled with real computed values — not free-form prose.
  • Competitors / market-share / segments have no clean free source → NA, plus
    GENERAL sector context explicitly labeled as opinion ("הערכה כללית לפי סקטור").
"""
import math

import pandas as pd
import yfinance as yf

import market
import risk as risk_engine
import decisions as dec
import trust as trust_engine
import technicals as ta
from ranking_engine.score import score_stock, score_breakdown
from ranking_engine.factor_scores import fundamental_score, sentiment_score
from ranking_engine.composite import composite_score
from ranking_engine.interpret import classify
from fundamentals.fundamentals import get_fundamentals
from backtesting.backtester import backtest_signal
from news.headlines import get_headlines
from news.sentiment import score_headlines
from names import get_company_name

NA = "אין נתון זמין"
DISCLAIMER = "מידע בלבד, לא ייעוץ השקעות."


def _num(v):
    return v if isinstance(v, (int, float)) and v == v and not math.isinf(v) else None


def _g(info, *keys):
    for k in keys:
        v = _num(info.get(k))
        if v is not None:
            return v
    return None


def _money(v):
    v = _num(v)
    if v is None:
        return NA
    for unit, d in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= d:
            return f"${v/d:.2f}{unit}"
    return f"${v:.0f}"


def _pct(v, dash=NA):
    v = _num(v)
    return f"{v:+.2f}%" if v is not None else dash


def _stmt_row(df, names):
    """Latest value of a statement row, trying several possible labels."""
    if df is None or not hasattr(df, "index"):
        return None
    for n in names:
        if n in df.index:
            try:
                s = df.loc[n].dropna()
                if len(s):
                    return float(s.iloc[0])
            except Exception:
                pass
    return None


# ---------------------------------------------------------------------------
# Pure rule-based opinion helpers (unit-tested, no network)
# ---------------------------------------------------------------------------

def valuation_class(valuation_score, peg, fwd_pe) -> str:
    """Undervalued / fair / overvalued from our valuation score (+ PEG/fwdPE)."""
    if valuation_score is None:
        return NA
    if valuation_score >= 65:
        return "מוערך בחסר (Undervalued)"
    if valuation_score >= 45:
        return "מתומחר בהוגן (Fairly valued)"
    return "מתומחר ביוקר (Overvalued)"


def recommendation(score_v2, risk_cat, valuation_score, trust_score) -> str:
    """Map composite V2 + risk + trust to a 6-level call (rule-based)."""
    if score_v2 is None:
        return NA
    lvl = ("Strong Buy" if score_v2 >= 78 else "Buy" if score_v2 >= 68
           else "Watch" if score_v2 >= 55 else "Hold" if score_v2 >= 45
           else "Reduce" if score_v2 >= 35 else "Avoid")
    order = ["Avoid", "Reduce", "Hold", "Watch", "Buy", "Strong Buy"]
    i = order.index(lvl)
    if risk_cat == "גבוה מאוד" and i > 1:           # very-high risk caps enthusiasm
        i -= 1
    if (trust_score or 0) < 40 and i > 1:            # low trust caps enthusiasm
        i -= 1
    he = {"Strong Buy": "קנייה חזקה", "Buy": "קנייה", "Watch": "מעקב",
          "Hold": "החזקה", "Reduce": "הקטנה", "Avoid": "להימנע"}
    return f"{order[i]} · {he[order[i]]}"


def scenario_probs(score_v2) -> dict:
    """Model-estimated scenario likelihood (NOT a market probability) derived
    deterministically from Score V2. Base case anchored at 40%; bull/bear tilt
    with the score. Always labeled in the UI as a model estimate."""
    v2 = score_v2 if isinstance(score_v2, (int, float)) and score_v2 == score_v2 else 50
    t = max(-1.0, min(1.0, (v2 - 50) / 50.0))
    bull = round(30 + t * 25)
    bear = round(30 - t * 25)
    return {"bull": bull, "base": 100 - bull - bear, "bear": bear}


def build_thesis(ctx: dict) -> dict:
    """Bull / base / bear cases — templates filled with the real numbers."""
    rg = _pct(ctx.get("rev_growth")) if ctx.get("rev_growth") is not None else NA
    eg = _pct(ctx.get("eps_growth")) if ctx.get("eps_growth") is not None else NA
    om = f"{ctx['op_margin']:.1f}%" if ctx.get("op_margin") is not None else NA
    val = ctx.get("valuation_label", NA)
    risk_cat = ctx.get("risk_cat", NA)
    bull = (f"אם הצמיחה נמשכת (הכנסות {rg}, רווח למניה {eg}) והשוליים התפעוליים ({om}) "
            f"נשמרים/משתפרים, ובהינתן מגמה טכנית {ctx.get('trend', NA)} — קיים פוטנציאל המשך עלייה.")
    base = (f"בתרחיש הבסיס: ציון סופי v2 {ctx.get('score_v2', NA)}, תמחור {val}, סיכון {risk_cat}. "
            f"ביצוע בקצב הסקטור, ללא הפתעה מהותית לכאן או לכאן.")
    bear = (f"בתרחיש השלילי: היחלשות צמיחה/שוליים, סיכון {risk_cat}"
            + (f", ביתא {ctx['beta']}" if ctx.get("beta") is not None else "")
            + (f", ירידה מקס׳ {ctx['maxdd']}%" if ctx.get("maxdd") is not None else "")
            + f". אם התמחור ({val}) מתברר כמתוח — אכזבה אפשרית.")
    return {"bull": bull, "base": base, "bear": bear}


def build_pros_cons(ctx: dict) -> dict:
    """5 strongest reasons for / against — derived from real metrics."""
    pros, cons = [], []
    if (ctx.get("fund") or 0) >= 65:
        pros.append(f"פונדמנטל חזק (ציון {ctx['fund']})")
    if (ctx.get("rev_growth") or 0) >= 15:
        pros.append(f"צמיחת הכנסות גבוהה ({ctx['rev_growth']:+.1f}%)")
    if (ctx.get("op_margin") or 0) >= 20:
        pros.append(f"רווחיות תפעולית גבוהה ({ctx['op_margin']:.1f}%)")
    if ctx.get("trend") in ("מגמת עלייה", "מגמת עלייה חזקה"):
        pros.append(f"מגמה טכנית חיובית ({ctx['trend']})")
    if ctx.get("risk_cat") in ("נמוך", "בינוני"):
        pros.append(f"פרופיל סיכון {ctx['risk_cat']}")
    if (ctx.get("valuation") or 0) >= 65:
        pros.append("תמחור אטרקטיבי (מוערך בחסר)")
    if (ctx.get("trust") or 0) >= 66:
        pros.append(f"אמון גבוה במערכת ({ctx['trust']})")

    if ctx.get("risk_cat") in ("גבוה", "גבוה מאוד"):
        cons.append(f"רמת סיכון {ctx['risk_cat']}")
    if (ctx.get("beta") or 0) > 1.3:
        cons.append(f"ביתא גבוהה ({ctx['beta']}) — תנודתי מול השוק")
    if ctx.get("maxdd") is not None and ctx["maxdd"] < -30:
        cons.append(f"ירידה מקסימלית עמוקה ({ctx['maxdd']}%)")
    if (ctx.get("valuation") or 100) < 45:
        cons.append("תמחור מתוח (יקר יחסית)")
    if ctx.get("trend") in ("מגמת ירידה", "מגמת ירידה חזקה"):
        cons.append(f"מגמה טכנית שלילית ({ctx['trend']})")
    if (ctx.get("rev_growth") is not None) and ctx["rev_growth"] < 0:
        cons.append(f"הכנסות מתכווצות ({ctx['rev_growth']:+.1f}%)")
    if (ctx.get("trust") or 100) < 40:
        cons.append("אמון נמוך — מעט אימות היסטורי")
    # pad to 5 honestly
    while len(pros) < 5:
        pros.append("—")
    while len(cons) < 5:
        cons.append("—")
    return {"pros": pros[:5], "cons": cons[:5]}


SECTOR_RISK_HE = {
    "Technology": ["רגולציית טכנולוגיה/אנטי-טראסט", "תחרות AI ומחזורי השקעה", "רגישות לריבית (מכפילים גבוהים)"],
    "Healthcare": ["רגולציה (FDA/מחירי תרופות)", "תוצאות ניסויים קליניים", "תביעות ופטנטים"],
    "Financial Services": ["רגישות לריבית ולמרווחים", "רגולציה בנקאית", "סיכון אשראי במיתון"],
    "Energy": ["תנודתיות מחירי נפט/גז", "רגולציה סביבתית", "מחזוריות מאקרו"],
    "Consumer Cyclical": ["רגישות למחזור הצריכה", "כוח קנייה ואינפלציה", "תחרות מחירים"],
    "Consumer Defensive": ["לחץ שוליים מאינפלציה", "כוח מיקוח קמעונאים", "צמיחה איטית"],
    "Communication Services": ["רגולציית תוכן/פרטיות", "תחרות פרסום", "רגישות מחזורית לפרסום"],
    "Industrials": ["מחזוריות מאקרו", "שרשרת אספקה", "חשיפה לסחר/מכסים"],
    "Utilities": ["רגישות גבוהה לריבית", "רגולציית תעריפים", "השקעות הון כבדות"],
    "Real Estate": ["רגישות גבוהה לריבית", "תפוסה וביקוש", "מינוף ומימון מחדש"],
    "Basic Materials": ["מחירי סחורות", "מחזוריות עולמית", "רגולציה סביבתית"],
}


# ---------------------------------------------------------------------------
# Hebrew description (real data → Hebrew; long summary auto-translated)
# ---------------------------------------------------------------------------

def translate_he(text):
    """Auto-translate English text to Hebrew (best-effort). None on any failure
    so the UI can fall back to the original — never invents content."""
    if not text or not isinstance(text, str):
        return None
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source="auto", target="iw").translate(text[:1500])
        return out or None
    except Exception:
        return None


def he_overview_line(name, sector_he, industry, country):
    """One factual Hebrew sentence built from REAL structured fields (always works)."""
    parts = [f"{name} פועלת"]
    if sector_he and sector_he != NA:
        parts.append(f"בסקטור {sector_he}")
    if industry and industry != NA:
        parts.append(f"(תחום: {industry})")
    line = " ".join(parts)
    if country and country != NA:
        line += f", ממוקמת ב-{country}"
    return line + "."


# ---------------------------------------------------------------------------
# Network fetch + assembly
# ---------------------------------------------------------------------------

def fetch_bundle(ticker: str) -> dict:
    """Live pull of everything we need for one ticker (caller should cache)."""
    t = ticker.strip().upper()
    tk = yf.Ticker(t)
    out = {"ticker": t}
    try:
        out["info"] = tk.info or {}
    except Exception:
        out["info"] = {}
    out["summary_he"] = translate_he((out["info"] or {}).get("longBusinessSummary"))
    try:
        out["hist"] = tk.history(period="5y", auto_adjust=True)
    except Exception:
        out["hist"] = None
    for attr in ("income_stmt", "balance_sheet", "cashflow"):
        try:
            out[attr] = getattr(tk, attr)
        except Exception:
            out[attr] = None
    try:
        out["mkt_close"] = yf.Ticker("^GSPC").history(period="5y", auto_adjust=True)["Close"]
    except Exception:
        out["mkt_close"] = None
    return out


def analyze(ticker: str, sectors=None, bundle=None) -> dict:
    """Assemble the full deep-dive report dict. `sectors` = precomputed sector
    intelligence (from market_overview.json) to avoid an extra live call."""
    b = bundle or fetch_bundle(ticker)
    t = b["ticker"]
    info = b.get("info") or {}
    hist = b.get("hist")
    if hist is None or "Close" not in getattr(hist, "columns", []) or hist["Close"].dropna().empty:
        return {"ticker": t, "error": f"לא נמצאו נתוני מחיר עבור '{t}'. בדוק את הסימול.", "disclaimer": DISCLAIMER}
    close = hist["Close"]
    mkt_close = b.get("mkt_close")

    # ---- Technicals ----
    ma = ta.moving_averages(close)
    rets = ta.returns(close)
    hl = ta.high_low_52w(close)
    rsi_last = ta._last(ta.rsi(close.dropna(), 14))
    macd = ta.macd(close)
    vol = ta.volume_analysis(hist)
    srl = getattr(ta, "sr_levels", lambda *_a, **_k: None)(hist)   # Phase 24 (guarded)
    sr = ({"support": srl["support"], "resistance": srl["resistance"]}
          if srl else ta.support_resistance(hist))
    cross = ta.cross_signal(close)
    atr = ta.atr(hist)
    vol_annual = risk_engine.volatility(close)
    maxdd = risk_engine.max_drawdown(close)
    beta = risk_engine.beta(close, mkt_close) if mkt_close is not None else None
    trend = ta.trend_class(ma.get("price"), ma.get("ma50"), ma.get("ma200"), rets.get("3m"))
    mom = ta.momentum_class(rsi_last, macd.get("hist"), rets.get("1m"))

    m = {"Price": ma.get("price"), "MA20": ma.get("ma20"), "MA50": ma.get("ma50"),
         "MA200": ma.get("ma200") or ma.get("ma50") or ma.get("price"),
         "RSI14": rsi_last or 50, "DistFromHigh%": hl.get("dist_from_high") or 0,
         "VolRatio": vol.get("ratio") or 0}
    tech_score = score_stock(m)
    tech_breakdown = score_breakdown(m)
    subs = ta.sub_scores(m, vol_annual, rets.get("3m"))

    # ---- Fundamentals / valuation ----
    fund = {}
    try:
        fund = get_fundamentals(t) or {}
    except Exception:
        fund = {}
    fund_score = fundamental_score(fund)
    val_score = dec.valuation_score(fund)
    rev_growth = _num(fund.get("RevenueGrowth"))
    eps_growth = _num(fund.get("EPSGrowth"))
    op_margin = _num(fund.get("OperatingMargin"))
    sector_en = fund.get("Sector") or info.get("sector")

    # ---- Scores ----
    sector_score = market.sector_score_for(sector_en, sectors or []) if sectors else None
    news = score_headlines(get_headlines(t, 5)) if True else {"score": 50}
    try:
        news = score_headlines(get_headlines(t, 5))
    except Exception:
        news = {"score": None}
    news_score = news.get("score")
    risk_score = risk_engine.risk_score(vol_annual, beta, maxdd)
    risk_cat = risk_engine.category(risk_score)
    comp = composite_score(technical=tech_score, fundamental=fund_score,
                           sector=sector_score, news=news_score, risk=risk_score)
    score_v2 = comp["final"] if comp else tech_score

    bt = backtest_signal(hist, mkt_close) if mkt_close is not None else None
    trust_row = {"Score": tech_score, "ScoreFundamental": fund_score, "ScoreSentiment": sentiment_score(m),
                 "Completeness": (comp["completeness"] * 100 if comp else 50),
                 "Beta": beta, "Volatility": vol_annual, "MaxDrawdown": maxdd}
    for k in trust_engine.FUND_FIELDS:
        trust_row[k] = fund.get(k)
    trust = trust_engine.trust_score(trust_row, bt)

    # ---- Opinion (rule-based) ----
    val_label = valuation_class(val_score, fund.get("PEG"), fund.get("ForwardPE"))
    rec = recommendation(score_v2, risk_cat, val_score, trust["score"])
    alloc = dec.target_allocation(score_v2, risk_cat, sector_score, "")
    ctx = {"score_v2": score_v2, "fund": fund_score, "valuation": val_score,
           "valuation_label": val_label, "risk_cat": risk_cat, "trust": trust["score"],
           "rev_growth": rev_growth, "eps_growth": eps_growth, "op_margin": op_margin,
           "trend": trend, "beta": beta, "maxdd": maxdd}
    thesis = build_thesis(ctx)
    proscons = build_pros_cons(ctx)

    # ---- Scenario cards (real analyst targets + model-estimated likelihood) ----
    probs = scenario_probs(score_v2)
    price_now = ma.get("price")

    def _tgt(key):
        tp = _g(info, key)
        if tp is None or not price_now:
            return {"price": NA, "price_num": None, "upside": None}
        return {"price": f"${tp:.0f}", "price_num": round(tp, 2),
                "upside": round((tp / price_now - 1) * 100, 1)}
    base_facts = [f"ציון סופי v2 {score_v2}", f"תמחור: {val_label}", f"רמת סיכון: {risk_cat}"]
    scenarios = [
        {"key": "bull", "emoji": "🟢", "title": "תרחיש שורי", "prob": probs["bull"],
         "target": _tgt("targetHighPrice"), "summary": thesis["bull"],
         "drivers": [d for d in proscons["pros"] if d != "—"][:4]},
        {"key": "base", "emoji": "🔵", "title": "תרחיש בסיס", "prob": probs["base"],
         "target": _tgt("targetMeanPrice"), "summary": thesis["base"], "drivers": base_facts},
        {"key": "bear", "emoji": "🔴", "title": "תרחיש דובי", "prob": probs["bear"],
         "target": _tgt("targetLowPrice"), "summary": thesis["bear"],
         "drivers": [d for d in proscons["cons"] if d != "—"][:4]},
    ]

    # ---- Financials (statements + info) ----
    inc, bs, cf = b.get("income_stmt"), b.get("balance_sheet"), b.get("cashflow")
    revenue = _stmt_row(inc, ["Total Revenue", "Operating Revenue"])
    gross = _stmt_row(inc, ["Gross Profit"])
    op_income = _stmt_row(inc, ["Operating Income", "Operating Income Or Loss"])
    net_income = _stmt_row(inc, ["Net Income", "Net Income Common Stockholders"])
    fcf = _stmt_row(cf, ["Free Cash Flow"]) or _g(info, "freeCashflow")
    debt = _stmt_row(bs, ["Total Debt"]) or _g(info, "totalDebt")
    cash = _stmt_row(bs, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]) or _g(info, "totalCash")
    margin = lambda part: round(part / revenue * 100, 1) if (part and revenue) else None

    financials = {
        "revenue": _money(revenue), "revenue_growth": _pct(rev_growth),
        "gross_profit": _money(gross), "gross_margin": (f"{margin(gross)}%" if margin(gross) is not None else NA),
        "operating_income": _money(op_income), "operating_margin": (f"{op_margin}%" if op_margin is not None else NA),
        "net_income": _money(net_income), "net_margin": (f"{margin(net_income)}%" if margin(net_income) is not None else NA),
        "eps": (f"${_g(info,'trailingEps'):.2f}" if _g(info, "trailingEps") is not None else NA),
        "eps_growth": _pct(eps_growth),
        "fcf": _money(fcf), "fcf_margin": (f"{margin(fcf)}%" if margin(fcf) is not None else NA),
        "debt": _money(debt), "cash": _money(cash),
        "debt_to_equity": (f"{fund.get('DebtToEquity')}" if _num(fund.get("DebtToEquity")) is not None else NA),
        "roe": (f"{_g(info,'returnOnEquity')*100:.1f}%" if _g(info, "returnOnEquity") is not None else NA),
        "roic": (f"{fund.get('ROIC')}%" if _num(fund.get("ROIC")) is not None else NA),
    }

    pfcf = (_g(info, "marketCap") / fcf) if (_g(info, "marketCap") and fcf and fcf > 0) else None
    valuation = {
        "forward_pe": (f"{_g(info,'forwardPE'):.1f}" if _g(info, "forwardPE") is not None else NA),
        "trailing_pe": (f"{_g(info,'trailingPE'):.1f}" if _g(info, "trailingPE") is not None else NA),
        "peg": (f"{fund.get('PEG')}" if _num(fund.get("PEG")) is not None else (f"{_g(info,'pegRatio')}" if _g(info, "pegRatio") is not None else NA)),
        "price_sales": (f"{_g(info,'priceToSalesTrailing12Months'):.1f}" if _g(info, "priceToSalesTrailing12Months") is not None else NA),
        "ev_ebitda": (f"{_g(info,'enterpriseToEbitda'):.1f}" if _g(info, "enterpriseToEbitda") is not None else NA),
        "price_fcf": (f"{pfcf:.1f}" if pfcf is not None else NA),
        "score": val_score, "label": val_label,
    }

    # ---- Growth / analyst (often NA on free data) ----
    target = _g(info, "targetMeanPrice")
    growth = {
        "analyst_target": (_money(target) if target is not None else NA),
        "analyst_count": (info.get("numberOfAnalystOpinions") or NA),
        "analyst_reco": (info.get("recommendationKey") or NA),
        "rev_estimate": NA, "eps_estimate": NA,   # not reliably free
        "earnings_date": _earnings_date(info),
        "trend": _growth_trend(rev_growth, eps_growth),
        "drivers": "מנועי צמיחה ספציפיים: אין נתון מובנה ממקור חינמי. הערכה כללית לפי הסקטור.",
    }

    sector_he = market.SECTOR_EN_TO_HE.get(sector_en, sector_en) if sector_en else None
    summary_en = info.get("longBusinessSummary")
    summary_he = b.get("summary_he")            # translated once at fetch (cached)
    if summary_he is None and bundle is None:    # direct call (no cached bundle) → try now
        summary_he = translate_he(summary_en)
    name = info.get("longName") or get_company_name(t) or t
    overview = {
        "name": name,
        "sector": sector_en or NA, "sector_he": sector_he or NA,
        "industry": info.get("industry") or NA,
        "summary": summary_en or NA,
        "summary_he": summary_he,
        "he_line": he_overview_line(name, sector_he, info.get("industry"), info.get("country")),
        "products": NA, "segments": NA,
        "geography": (info.get("country") or NA),
    }

    market_data = {
        "price": (f"${ma.get('price'):.2f}" if ma.get("price") is not None else NA),
        "market_cap": _money(_g(info, "marketCap")),
        "high_52w": (f"${hl['high']}" if hl.get("high") is not None else NA),
        "low_52w": (f"${hl['low']}" if hl.get("low") is not None else NA),
        "daily_change": _pct((close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else None),
        "ret_1w": _pct(rets.get("1w")), "ret_1m": _pct(rets.get("1m")), "ret_3m": _pct(rets.get("3m")),
        "ret_6m": _pct(rets.get("6m")), "ytd": _pct(rets.get("ytd")), "ret_1y": _pct(rets.get("1y")),
        "ret_3y": _pct(rets.get("3y")),
    }

    technicals = {
        "trend": trend, "momentum": mom, "rsi": (round(rsi_last, 1) if rsi_last is not None else NA),
        "macd": macd, "atr": (atr if atr is not None else NA), "cross": cross,
        "moving_averages": ma, "returns": rets, "high_low": hl, "volume": vol,
        "support_resistance": sr, "sr_levels": srl,
        "beta": (beta if beta is not None else NA),
        "volatility": (vol_annual if vol_annual is not None else NA),
        "max_drawdown": (maxdd if maxdd is not None else NA),
        "risk_category": risk_cat, "sub_scores": subs,
        "opinion": _tech_opinion(trend, mom, rsi_last, hl.get("dist_from_high"), sr, ma.get("price")),
    }

    raw_metrics = {
        "price": ma.get("price"), "rev_growth": rev_growth, "eps_growth": eps_growth,
        "op_margin": op_margin, "fcf_growth": _num(fund.get("FCFGrowth")),
        "debt_equity": _num(fund.get("DebtToEquity")), "roic": _num(fund.get("ROIC")),
        "ret_3m": rets.get("3m"), "ret_1m": rets.get("1m"), "rsi": rsi_last,
    }

    return {
        "ticker": t, "disclaimer": DISCLAIMER,
        "raw_metrics": raw_metrics,
        "overview": overview, "market_data": market_data, "financials": financials,
        "valuation": valuation, "growth": growth,
        "competitive": {
            "competitors": NA, "market_share": NA, "moat": NA,
            "note": "מתחרים/נתח שוק/חפיר: אין מקור חינמי מובנה ואמין → לא ממציאים. "
                    + "הערכה כללית לפי הסקטור בלבד.",
        },
        "regulation_risks": {"sector_risks": SECTOR_RISK_HE.get(sector_en, ["סיכוני מאקרו כלליים", "רגישות לריבית", "תחרות בענף"]),
                             "label": "הערכה כללית לפי סקטור (דעה)"},
        "technicals": technicals,
        "risk": {"beta": beta, "volatility": vol_annual, "max_drawdown": maxdd,
                 "risk_score": risk_score, "category": risk_cat,
                 "warnings": risk_engine.risk_profile(close, mkt_close).get("warnings", []) if mkt_close is not None else []},
        "scores": _scores_block(tech_score, fund_score, sector_score, news_score, risk_score, score_v2, trust, val_score, comp),
        "thesis": thesis, "pros_cons": proscons,
        "scenarios": scenarios,
        "confidence": {"score": trust["score"], "category": trust["category"]},
        "opinion": {
            "recommendation": rec, "allocation_pct": alloc,
            "valuation_label": val_label,
            "attractive": _attractive_text(score_v2, val_score, risk_cat),
            "what_changes": "שינוי מהותי בצמיחה/שוליים, פריצת/שבירת רמות טכניות מרכזיות, "
                            "או שינוי בתמחור (מכפילים) — ישנו את ההמלצה.",
            "investor_profile": _investor_profile(risk_cat, vol_annual),
        },
        "meta": {"completeness": (comp["completeness"] if comp else None),
                 "facts": "נמשך מ-Yahoo Finance", "calc": "מחושב במנועי המערכת",
                 "opinion_note": "תזה/דעה — מבוססת כללים על נתונים אמיתיים, לא ייעוץ"},
    }


def _earnings_date(info):
    ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
    if not ts:
        return NA
    try:
        return pd.to_datetime(ts, unit="s").strftime("%d/%m/%Y")   # Israeli DD/MM/YYYY
    except Exception:
        return NA


def _growth_trend(rev_g, eps_g):
    vals = [v for v in (rev_g, eps_g) if v is not None]
    if not vals:
        return NA
    avg = sum(vals) / len(vals)
    return "מאיץ" if avg >= 20 else "צומח" if avg >= 5 else "יציב" if avg >= 0 else "מתכווץ"


def _tech_opinion(trend, mom, rsi, dist_high, sr, price):
    bits = [f"מצב טכני: {trend}, מומנטום {mom}."]
    if rsi is not None:
        if rsi >= 75:
            bits.append(f"RSI {rsi:.0f} — קנוי-יתר, מתוח בטווח הקצר.")
        elif rsi <= 30:
            bits.append(f"RSI {rsi:.0f} — מכור-יתר.")
    if dist_high is not None and dist_high <= 3:
        bits.append("קרוב מאוד לשיא 52 שבועות (מצב פריצה אפשרי).")
    if sr.get("support") and price:
        bits.append(f"תמיכה קרובה ${sr['support']}, התנגדות {('$'+str(sr['resistance'])) if sr.get('resistance') else NA}.")
    bits.append("יחס סיכון/סיכוי תלוי בכניסה ביחס לתמיכה/התנגדות שלעיל.")
    return " ".join(bits)


def _attractive_text(score_v2, val_score, risk_cat):
    a = "אטרקטיבי" if (score_v2 or 0) >= 65 else "בינוני" if (score_v2 or 0) >= 50 else "פחות אטרקטיבי"
    v = "זול" if (val_score or 0) >= 65 else "סביר" if (val_score or 0) >= 45 else "יקר"
    return f"כרגע נראה {a} (ציון v2 {score_v2}), בתמחור {v}, ברמת סיכון {risk_cat}."


def _investor_profile(risk_cat, vol):
    if risk_cat in ("גבוה", "גבוה מאוד") or (vol or 0) > 45:
        return "מתאים למשקיע אגרסיבי/סובל-סיכון, עם אופק ארוך וסבילות לתנודתיות."
    if risk_cat == "נמוך":
        return "מתאים גם למשקיע שמרני/מאוזן."
    return "מתאים למשקיע מאוזן עם אופק בינוני-ארוך."


def _explain(key):
    return {
        "technical": "מבנה מגמה, RSI, נפח וקרבה לשיא (0-100).",
        "fundamental": "צמיחה, שוליים, חוב, ROIC, PEG, מכפיל (0-100).",
        "sector": "חוזק הסקטור של המניה מול S&P (0-100).",
        "news": "סנטימנט כותרות (50=ניטרלי).",
        "risk": "תנודתיות+ביתא+Drawdown (גבוה=מסוכן).",
        "v2": "שקלול: פונד׳ 35% · טכני 25% · סקטור 20% · חדשות 10% · סיכון 10%.",
        "trust": "אמון מ-7 גורמים (אימות, מדגם, OOS, שלמות).",
        "valuation": "PEG+מכפיל עתידי (גבוה=זול יותר).",
    }.get(key, "")


NOT_ENOUGH = "אין מספיק נתונים"


def _rr_interpretation(rr):
    if rr is None:
        return None
    return ("מצוין" if rr >= 2.5 else "טוב" if rr >= 1.5 else "סביר" if rr >= 1.0 else "חלש")


def _entry_quality(trend, rsi, dist_sup, dist_res, rr, val_score):
    """Rule-based entry quality: (emoji, label, band, reasons[]). All from real metrics."""
    reasons = []
    if dist_sup is not None:
        reasons.append(f"המחיר {abs(dist_sup):.1f}% מעל התמיכה")
    if dist_res is not None:
        reasons.append(f"{dist_res:.1f}% עד ההתנגדות")
    if rr is not None:
        reasons.append(f"יחס סיכון/סיכוי {rr}")
    if isinstance(val_score, (int, float)):
        reasons.append("התמחור אטרקטיבי" if val_score >= 65 else
                       "התמחור סביר" if val_score >= 40 else "התמחור יקר יחסית")
    if trend in ("מגמת ירידה", "מגמת ירידה חזקה"):
        return "🔴", "להימנע מרדיפה", "avoid", [f"מגמה טכנית שלילית ({trend})"] + reasons[:2]
    if (isinstance(rsi, (int, float)) and rsi >= 75) or (dist_res is not None and dist_res <= 2):
        return "🟠", "מתוח — התרחק מרמות אלו", "extended", \
            ([f"RSI {rsi:.0f} — קנוי-יתר"] if isinstance(rsi, (int, float)) and rsi >= 75 else []) + reasons[:3]
    if dist_sup is not None and abs(dist_sup) <= 3 and (rr or 0) >= 2:
        return "🟢", "נקודת כניסה מצוינת", "excellent", reasons[:4]
    if dist_sup is not None and abs(dist_sup) <= 6 and (rr or 0) >= 1.2:
        return "🟢", "כניסה טובה", "good", reasons[:4]
    if rr is not None and rr < 1:
        return "🟡", "עדיף להמתין לתיקון", "wait", reasons[:4]
    return "🟡", "ניטרלי — אין יתרון כניסה מובהק", "wait", (reasons[:4] or [NOT_ENOUGH])


def _check(value, good, neutral, higher_better=True):
    """Checklist status for one metric: good/neutral/weak/na."""
    if not isinstance(value, (int, float)) or value != value:
        return "na"
    if higher_better:
        return "good" if value >= good else ("neutral" if value >= neutral else "weak")
    return "good" if value <= good else ("neutral" if value <= neutral else "weak")


def investment_decision(rep: dict, regime_score=None) -> dict:
    """Assemble the Investment Decision summary — PURE derivation from the report.

    No new information: everything comes from metrics already computed in
    analyze() (scores, analyst targets, support/resistance, fundamentals).
    Missing inputs surface as None / "אין מספיק נתונים" — never fabricated.
    """
    rm = rep.get("raw_metrics") or {}
    sc = rep.get("scores") or {}
    srl = (rep.get("technicals") or {}).get("sr_levels") or {}
    tech = rep.get("technicals") or {}
    rk = rep.get("risk") or {}
    op = rep.get("opinion") or {}
    scen = {s.get("key"): s for s in rep.get("scenarios", [])}
    base_t = (scen.get("base") or {}).get("target") or {}

    def _sv(key):
        v = (sc.get(key) or {}).get("value")
        return v if isinstance(v, (int, float)) else None

    v2, fund_s, tech_s = _sv("final_v2"), _sv("fundamental"), _sv("technical")
    val_s, sector_s, trust_s = _sv("valuation"), _sv("sector"), _sv("trust")
    risk_score = rk.get("risk_score")
    price = rm.get("price") or srl.get("price")

    # Fair value = analyst consensus mean target (real data, labeled as such).
    fair = base_t.get("price_num")
    upside = base_t.get("upside")                       # % to consensus target
    mos = round((fair - price) / fair * 100, 1) if (fair and price and fair > 0) else None
    downside = srl.get("dist_support_pct")              # % to support (negative)
    rr = (round(upside / abs(downside), 2)
          if (isinstance(upside, (int, float)) and isinstance(downside, (int, float))
              and upside > 0 and abs(downside) > 0.05) else srl.get("risk_reward"))

    trend = tech.get("trend")
    entry = _entry_quality(trend, rm.get("rsi"), downside, srl.get("dist_resistance_pct"),
                           srl.get("risk_reward"), val_s)

    # Horizon (rule-based from setup character).
    ret3 = rm.get("ret_3m")
    risk_cat = rk.get("category")
    if srl.get("status") == "breakout" or ((ret3 or 0) >= 30 and risk_cat in ("גבוה", "גבוה מאוד")):
        horizon = "סווינג / 3 חודשים"
    elif (fund_s or 0) >= 70 and risk_cat in ("נמוך", "בינוני"):
        horizon = "טווח ארוך (12+ חודשים)"
    elif (fund_s or 0) >= 55:
        horizon = "6–12 חודשים"
    else:
        horizon = "3–6 חודשים"

    mom_sub = (tech.get("sub_scores") or {}).get("momentum")
    checklist = [
        ("צמיחה", rm.get("rev_growth"), _check(rm.get("rev_growth"), 15, 5), "%"),
        ("רווחיות (ROIC)", rm.get("roic"), _check(rm.get("roic"), 15, 8), "%"),
        ("שוליים", rm.get("op_margin"), _check(rm.get("op_margin"), 20, 10), "%"),
        ("תזרים מזומנים", rm.get("fcf_growth"), _check(rm.get("fcf_growth"), 10, 0), "%"),
        ("חוב", rm.get("debt_equity"), _check(rm.get("debt_equity"), 0.5, 1.5, higher_better=False), "x"),
        ("תמחור", val_s, _check(val_s, 65, 40), ""),
        ("מומנטום", ret3, _check(ret3, 15, 0), "%"),
        ("מגמה", trend, ("good" if isinstance(trend, str) and "עלייה" in trend else
                         "weak" if isinstance(trend, str) and "ירידה" in trend else
                         "neutral" if trend else "na"), ""),
        ("מבנה טכני", tech_s, _check(tech_s, 66, 40), ""),
        ("חוזק סקטור", sector_s, _check(sector_s, 66, 40), ""),
        ("סביבת מאקרו", regime_score, _check(regime_score, 60, 40), ""),
        ("סיכון", risk_score, _check(risk_score, 32, 65, higher_better=False), ""),
    ]

    matrix = {"פונדמנטלי": fund_s, "טכני": tech_s, "תמחור": val_s,
              "מומנטום": mom_sub, "סיכון (בריאות)": (100 - risk_score) if isinstance(risk_score, (int, float)) else None,
              "סקטור": sector_s}

    # Investor-type tags (rule-based).
    tags = []
    if (rm.get("rev_growth") or 0) >= 20 or (rm.get("eps_growth") or 0) >= 25:
        tags.append("משקיע צמיחה")
    if (val_s or 0) >= 65:
        tags.append("משקיע ערך")
    if (ret3 or 0) >= 30:
        tags.append("סוחר מומנטום")
    if (fund_s or 0) >= 60 and risk_cat == "נמוך":
        tags.append("משקיע טווח ארוך")
    if entry[2] in ("excellent", "good") and (srl.get("risk_reward") or 0) >= 2:
        tags.append("סוחר סווינג")
    if not tags:
        tags.append("פרופיל מעורב — לא מובהק")

    # What must happen (only for actually-weak items).
    wait_for = []
    if isinstance(val_s, (int, float)) and val_s < 40:
        wait_for.append("התכווצות תמחור (ירידת מכפילים) או ירידת מחיר לכיוון התמיכה"
                        + (f" ${srl['support']}" if srl.get("support") else ""))
    if srl.get("dist_resistance_pct") is not None and srl["dist_resistance_pct"] <= 4 and srl.get("resistance"):
        wait_for.append(f"פריצה מבוססת מעל ההתנגדות ${srl['resistance']}")
    if isinstance(rm.get("rev_growth"), (int, float)) and rm["rev_growth"] < 5:
        wait_for.append("האצת צמיחת הכנסות")
    if isinstance(rm.get("op_margin"), (int, float)) and rm["op_margin"] < 10:
        wait_for.append("שיפור שולי רווח תפעוליים")
    if isinstance(rm.get("debt_equity"), (int, float)) and rm["debt_equity"] > 1.5:
        wait_for.append("הפחתת מינוף (חוב/הון)")
    if isinstance(trend, str) and "ירידה" in trend:
        wait_for.append("חזרה למגמת עלייה (התייצבות מעל ממוצע 200)")
    if not wait_for:
        wait_for.append("אין תנאי-סף מהותיים — המדדים הנוכחיים כבר תומכים")

    # What could go wrong (only data-supported risks).
    risks = []
    if isinstance(val_s, (int, float)) and val_s < 40:
        risks.append("סיכון תמחור — מכפילים מתוחים ביחס לצמיחה")
    if isinstance(rk.get("beta"), (int, float)) and rk["beta"] > 1.3:
        risks.append(f"רגישות גבוהה לשוק (ביתא {rk['beta']})")
    if isinstance(rm.get("debt_equity"), (int, float)) and rm["debt_equity"] > 1.5:
        risks.append(f"מינוף גבוה (חוב/הון {rm['debt_equity']})")
    if isinstance(sector_s, (int, float)) and sector_s < 40:
        risks.append("חולשה סקטוריאלית — רוח נגדית ענפית")
    if isinstance(rk.get("max_drawdown"), (int, float)) and rk["max_drawdown"] < -35:
        risks.append(f"תנודתיות היסטורית עמוקה (ירידה מקס׳ {rk['max_drawdown']}%)")
    if isinstance(trust_s, (int, float)) and trust_s < 40:
        risks.append("אימות היסטורי מוגבל — מדגם קטן")
    for x in (rep.get("regulation_risks") or {}).get("sector_risks", [])[:2]:
        if len(risks) < 5:
            risks.append(f"{x} (הערכה כללית לפי סקטור)")

    # Price zones (visual positions 0-100 across the observed range).
    zones = None
    nums = [x for x in (srl.get("support"), srl.get("resistance"), price, fair) if isinstance(x, (int, float))]
    if price and len(nums) >= 3:
        lo, hi = min(nums) * 0.99, max(nums) * 1.01
        rngz = (hi - lo) or 1.0
        posz = lambda x: round((x - lo) / rngz * 100, 1) if isinstance(x, (int, float)) else None
        zones = {"lo": round(lo, 2), "hi": round(hi, 2),
                 "support": srl.get("support"), "resistance": srl.get("resistance"),
                 "price": price, "fair": fair,
                 "pos_support": posz(srl.get("support")), "pos_resistance": posz(srl.get("resistance")),
                 "pos_price": posz(price), "pos_fair": posz(fair)}

    strengths = [x for x in (rep.get("pros_cons") or {}).get("pros", []) if x != "—"][:5]
    weaknesses = [x for x in (rep.get("pros_cons") or {}).get("cons", []) if x != "—"][:5]

    return {
        "recommendation": op.get("recommendation", NOT_ENOUGH),
        "confidence": trust_s, "horizon": horizon,
        "price": price, "target": base_t.get("price", NA), "target_num": fair,
        "fair_value": base_t.get("price", NA), "margin_of_safety": mos,
        "support": srl.get("support"), "resistance": srl.get("resistance"),
        "upside": upside, "downside": downside, "rr": rr,
        "rr_interpretation": _rr_interpretation(rr),
        "risk_level": risk_cat or NOT_ENOUGH, "score_v2": v2,
        "entry": {"emoji": entry[0], "label": entry[1], "band": entry[2], "reasons": entry[3]},
        "checklist": checklist, "matrix": matrix,
        "investor_types": tags, "wait_for": wait_for[:4], "risks": risks[:5],
        "zones": zones, "strengths": strengths, "weaknesses": weaknesses,
    }


def _scores_block(tech, fund, sector, news, risk, v2, trust, valuation, comp):
    return {
        "final_v2": {"value": v2, "explain": _explain("v2"),
                     "contributions": comp["contributions"] if comp else {}},
        "technical": {"value": tech, "explain": _explain("technical")},
        "fundamental": {"value": fund if fund is not None else NA, "explain": _explain("fundamental")},
        "sector": {"value": sector if sector is not None else NA, "explain": _explain("sector")},
        "news": {"value": news if news is not None else NA, "explain": _explain("news")},
        "risk": {"value": risk if risk is not None else NA, "explain": _explain("risk")},
        "trust": {"value": trust["score"], "category": trust["category"], "explain": _explain("trust"),
                  "strengths": trust["strengths"], "limitations": trust["limitations"]},
        "valuation": {"value": valuation if valuation is not None else NA, "explain": _explain("valuation")},
    }
