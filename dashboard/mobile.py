# -*- coding: utf-8 -*-
"""Mobile-first UI (Phase 26 redesign).

A true mobile investment-app experience — NOT a compressed desktop dashboard:
sticky BOTTOM navigation, one-question-per-screen pages, large type (body 16px,
titles 20px, key metrics 28px+), 48px touch targets, no wide tables, no
horizontal overflow, charts lazy-rendered behind a toggle. Session-state
navigation (m_page + _m_pending) so any card can deep-link into Company
Analysis. Reuses the same engines/artifacts as desktop — zero logic changes.
"""
import json
import os
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import market
import technicals as ta
from ranking_engine.interpret import classify
from dashboard import views as VW
from dashboard.theme import (GREEN, AMBER, RED, BLUE, BG, CARD, ELEV, BORDER, MUTED, TEXT,
                             PRIMARY, POSITIVE, WARNING, NEGATIVE, SECONDARY,
                             score_color, score_bar, style_fig)

MOBILE_CSS = f"""
<style>
  .stApp {{ background:{BG}; font-size:16px; }}
  section[data-testid="stSidebar"] {{ display:none; }}
  .block-container {{ padding:0.6rem 0.75rem 108px !important; max-width:100% !important; }}
  html, body, .stApp {{ overflow-x:hidden; }}
  * {{ direction:rtl; }}
  h1,h2,h3,h4,p,div,span,li {{ text-align:right; color:{TEXT}; }}
  h3, h4 {{ font-size:20px; font-weight:700; margin:1.2rem 0 .5rem; }}
  .sticky {{ position:sticky; top:0; z-index:99; background:{CARD}; border-bottom:1px solid {BORDER};
            padding:11px 13px; margin:-0.6rem -0.75rem 8px; font-size:15px; }}
  .mcard {{ background:{CARD}; border:none; border-radius:16px; padding:16px 18px; margin:10px 0; }}
  .mtick {{ font-size:22px; font-weight:800; }}
  .mrec {{ font-size:15px; font-weight:700; float:left; }}
  .mco {{ color:{SECONDARY}; font-size:15px; margin:3px 0; line-height:1.55; }}
  .mstats {{ font-size:16px; margin:8px 0; }}
  .mwhy {{ color:{SECONDARY}; font-size:15px; line-height:1.6; }}
  .big {{ font-size:32px; font-weight:800; line-height:1.1; }}
  .stButton button {{ min-height:48px; font-size:16px; border-radius:12px; width:100%; }}
  .stButton button:active {{ transform:scale(.985); }}
  div[data-testid="stMetricValue"] {{ font-size:1.6rem; }}
  details summary {{ font-size:17px; font-weight:700; min-height:48px; display:flex; align-items:center; }}
  /* KPI grid → 2-up, larger */
  .kpi-grid {{ grid-template-columns:repeat(2,1fr) !important; gap:10px; }}
  .kpi .k-val {{ font-size:28px !important; }}
  .kpi .k-lab, .kpi .k-sub {{ font-size:14.5px !important; }}
  /* horizontal chip rows (performance / period pills) */
  .chiprow {{ display:flex; gap:8px; overflow-x:auto; padding:4px 0 8px; white-space:nowrap;
              scrollbar-width:none; }}
  .chiprow::-webkit-scrollbar {{ display:none; }}
  .chip {{ flex:0 0 auto; background:{CARD}; border-radius:999px; padding:9px 15px;
           font-size:15px; font-weight:700; }}
  /* period selector radio → scrollable pills */
  div[data-testid="stRadio"] [role="radiogroup"] {{ flex-wrap:nowrap; overflow-x:auto; gap:8px;
       scrollbar-width:none; }}
  div[data-testid="stRadio"] [role="radiogroup"]::-webkit-scrollbar {{ display:none; }}
  div[data-testid="stRadio"] [role="radiogroup"] label {{ background:{CARD}; border:none;
       border-radius:999px; padding:9px 15px; white-space:nowrap; font-size:15px; font-weight:600;
       min-height:44px; }}
  div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {{
       background:{PRIMARY}; }}
  div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) * {{ color:#0B1220 !important; }}
  /* ---- Sticky BOTTOM navigation (real-app feel) ---- */
  .st-key-mnav {{ position:fixed; bottom:0; left:0; right:0; z-index:999;
       background:{CARD}; border-top:1px solid {BORDER};
       padding:6px 6px calc(8px + env(safe-area-inset-bottom)); margin:0; }}
  .st-key-mnav [role="radiogroup"] {{ display:flex; justify-content:space-around;
       flex-wrap:nowrap; overflow-x:auto; gap:2px; }}
  .st-key-mnav [role="radiogroup"] label {{ background:transparent !important; border:none;
       border-radius:12px; padding:7px 9px; min-height:48px; font-size:13.5px; font-weight:600;
       display:flex; align-items:center; }}
  .st-key-mnav [role="radiogroup"] label:has(input:checked) {{ background:{ELEV} !important; }}
  .st-key-mnav [role="radiogroup"] label:has(input:checked) * {{ color:{PRIMARY} !important; }}
  .scen {{ margin-bottom:10px; }}
</style>
"""

PAGES = ["🏠 בית", "🔎 ניתוח", "💎 הזדמנויות", "🗺️ סקטורים", "🚨 התראות", "⚙️"]


def _fmt(v, suf="", dash="—"):
    if v is None or (isinstance(v, float) and v != v):
        return dash
    return f"{v}{suf}"


def _num(v):
    return v if isinstance(v, (int, float)) and v == v else None


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return default
    return default


@st.cache_data(ttl=1800, show_spinner=False)
def _dd_fetch(ticker):
    import deepdive
    return deepdive.fetch_bundle(ticker)


def _goto(page, ticker=None, key=None, label=None):
    """Full-width action button that deep-links to a mobile page."""
    if st.button(label or page, key=key or f"go_{page}_{ticker}", use_container_width=True):
        if ticker:
            st.session_state["dd_ticker"] = ticker
        st.session_state["_m_pending"] = page
        st.rerun()


def _mkpi(ico, val, lab, sub, ac):
    return (f"<div class='kpi' style='--ac:{ac}'><div class='k-ico'>{ico}</div>"
            f"<div class='k-val'>{val}</div>"
            f"<div class='k-lab'>{lab}</div><div class='k-sub'>{sub}</div></div>")


def _grid(cards, cols=2):
    return f"<div class='kpi-grid' style='grid-template-columns:repeat({cols},1fr)'>{''.join(cards)}</div>"


def _opp_card(r, lookup, nc, key_prefix="m"):
    info = classify(r)
    tk = r["Ticker"]
    nm = VW.company_name(tk, lookup, nc)
    chg = r.get("DailyChange%", 0) or 0
    ccol = POSITIVE if chg >= 0 else NEGATIVE
    sv = _num(r.get("ScoreV2", r.get("Score")))
    rb = VW.risk_badge(r.get("RiskLevel"))
    sec_he = market.SECTOR_EN_TO_HE.get(r.get("Sector"), r.get("Sector") or "")
    extra = []
    if _num(r.get("Valuation")) is not None:
        extra.append(f"תמחור <b>{int(r['Valuation'])}</b>")
    if _num(r.get("Ret3m")) is not None:
        extra.append(f"מומנטום <b style='color:{POSITIVE if r['Ret3m'] >= 0 else NEGATIVE}'>"
                     f"{'+' if r['Ret3m'] >= 0 else ''}{int(r['Ret3m'])}%</b>")
    st.markdown(
        f"""<div class="mcard" style="border-right:4px solid {info['color']}">
          <div><span class="mtick">{tk}</span>
            <span class="mrec" style="color:{info['color']}">{info['emoji']} {info['label']}</span></div>
          <div class="mco">{nm}{(' · ' + sec_he) if sec_he else ''}</div>
          <div class="mstats">ציון V2 <b style="color:{score_color(sv)}">{int(sv) if sv is not None else '—'}</b> ·
            <span style="color:{rb[3]}">{rb[0]} {rb[1]}</span> ·
            <span style="color:{ccol}">{'+' if chg >= 0 else ''}{chg}%</span>
            {(' · ' + ' · '.join(extra)) if extra else ''}</div>
          <div class="mwhy">{info['summary']}</div>
        </div>""", unsafe_allow_html=True)
    _goto("🔎 ניתוח", tk, key=f"{key_prefix}_an_{tk}", label=f"🔎 ניתוח {tk}")


# ---------------------------------------------------------------------------

def render(df, mkt):
    """Entry point: the mobile app experience (bottom-nav driven)."""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    alerts = _load(config.ALERTS_CENTER_JSON, [])
    uni = _load(config.UNIVERSE_JSON, {})
    sysh = _load(config.SYSTEM_HEALTH_JSON, {})
    df = df.copy()
    df["_g"] = [classify(r)["group"] for _, r in df.iterrows()]
    regime = mkt.get("regime", {})
    fng = mkt.get("fear_greed", {})
    sectors = sorted(mkt.get("sectors", []), key=lambda s: -s.get("score", 0))
    lookup = VW.build_lookup(uni)
    nc = VW.names_cache()

    reg_s = regime.get("score", "—")
    rcol = POSITIVE if isinstance(reg_s, (int, float)) and reg_s >= 60 else \
        (NEGATIVE if isinstance(reg_s, (int, float)) and reg_s < 40 else WARNING)
    st.markdown(f"<div class='sticky'>🤖 <b>Stock Agent</b> · מצב שוק "
                f"<b style='color:{rcol}'>{reg_s}</b> · פחד/חמדנות {fng.get('score', '—')}</div>",
                unsafe_allow_html=True)

    # Bottom navigation (sticky, app-like). _m_pending applied BEFORE the widget.
    if st.session_state.get("_m_pending"):
        st.session_state["m_page"] = st.session_state.pop("_m_pending")
    with st.container(key="mnav"):
        page = st.radio("ניווט", PAGES, horizontal=True, key="m_page", label_visibility="collapsed")

    pos = df[df["_g"] == "positive"].sort_values("ScoreV2", ascending=False)
    ranked = pos if not pos.empty else df.sort_values("ScoreV2", ascending=False)

    if page == "🏠 בית":
        _home(df, ranked, sectors, alerts, regime, fng, lookup, nc)
    elif page == "🔎 ניתוח":
        _analysis(mkt, lookup, nc)
    elif page == "💎 הזדמנויות":
        _opportunities(df, uni, lookup, nc)
    elif page == "🗺️ סקטורים":
        _sectors(uni, mkt)
    elif page == "🚨 התראות":
        _alerts(alerts)
    else:
        _settings(df, mkt, sysh)

    st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")


# ---------------------------------------------------------------------------

def _home(df, ranked, sectors, alerts, regime, fng, lookup, nc):
    """Home = 6 focused cards: regime, F&G, top-3, sector, main alert, decision CTA."""
    reg_s = regime.get("score")
    fg = fng.get("score")
    fgc = (NEGATIVE if isinstance(fg, (int, float)) and fg < 45
           else POSITIVE if isinstance(fg, (int, float)) and fg > 55 else WARNING)
    st.markdown(_grid([
        _mkpi("🧭", _fmt(reg_s), "מצב שוק", regime.get("label", ""),
              POSITIVE if (reg_s or 0) >= 60 else NEGATIVE if (reg_s or 0) < 40 else WARNING),
        _mkpi("😶‍🌫️", _fmt(fg), "פחד / חמדנות", fng.get("label", ""), fgc),
    ]), unsafe_allow_html=True)

    st.markdown("#### 3 ההזדמנויות המובילות")
    for _, r in ranked.head(3).iterrows():
        _opp_card(r, lookup, nc, key_prefix="h")

    if sectors:
        s = sectors[0]
        st.markdown(f"<div class='mcard' style='border-right:4px solid {POSITIVE}'>"
                    f"<div class='mco'>הסקטור החזק ביותר</div>"
                    f"<div class='big' style='color:{POSITIVE}'>{s['sector']}</div>"
                    f"<div class='mco'>ציון {s['score']} · מומנטום {s.get('momentum', '—')}</div></div>",
                    unsafe_allow_html=True)
        _goto("🗺️ סקטורים", key="h_sec", label="כל הסקטורים")

    crit = [a for a in alerts if a.get("severity") == "גבוהה"]
    if crit:
        a = crit[0]
        st.markdown(f"<div class='mcard' style='border-right:4px solid {NEGATIVE}'>"
                    f"<div class='mco'>ההתראה המרכזית</div>"
                    f"<div style='font-size:18px;font-weight:700'>{a['type']} · {a.get('scope', '')}</div>"
                    f"<div class='mco'>{a['message']}</div></div>", unsafe_allow_html=True)
        _goto("🚨 התראות", key="h_al", label=f"כל ההתראות ({len(alerts)})")

    if len(ranked):
        top_tk = ranked.iloc[0]["Ticker"]
        st.markdown(f"<div class='mcard' style='border-right:4px solid {PRIMARY}'>"
                    f"<div class='mco'>קיצור דרך</div>"
                    f"<div style='font-size:18px;font-weight:700'>החלטת השקעה מלאה ל-{top_tk}</div>"
                    f"<div class='mco'>המלצה, איכות כניסה, יעד, רמות ויחס סיכון/סיכוי.</div></div>",
                    unsafe_allow_html=True)
        _goto("🔎 ניתוח", top_tk, key="h_dec", label=f"🔎 פתח החלטת השקעה · {top_tk}")


def _opportunities(df, uni, lookup, nc):
    base = pd.DataFrame(uni.get("opportunities", []))
    if base.empty:                       # fallback to the watchlist
        base = df.sort_values("ScoreV2", ascending=False)
    with st.expander("⚙️ סינון מתקדם"):
        secs = sorted([s for s in base.get("Sector", pd.Series()).dropna().unique()])
        f_sec = st.selectbox("סקטור", ["הכל"] + secs, key="m_sec")
        f_risk = st.multiselect("רמת סיכון", ["נמוך", "בינוני", "גבוה", "גבוה מאוד"], key="m_risk")
        SC = {"הכל": 0, "60+": 60, "70+": 70, "80+": 80}
        f_score = SC[st.selectbox("ציון מינימלי (Score V2)", list(SC), key="m_score")]
    v = base
    if f_sec != "הכל" and "Sector" in v:
        v = v[v["Sector"] == f_sec]
    if f_risk and "RiskLevel" in v:
        v = v[v["RiskLevel"].isin(f_risk)]
    if "ScoreV2" in v:
        v = v[v["ScoreV2"].fillna(0) >= f_score].sort_values("ScoreV2", ascending=False)
    st.markdown(f"**נמצאו {len(v)} מניות**")
    if v.empty:
        st.info("אין מניות שעוברות את הסינון. נסה להרחיב את התנאים.")
    for _, r in v.head(20).iterrows():
        _opp_card(r, lookup, nc, key_prefix="o")


def _sectors(uni, mkt):
    st.markdown("#### סקטורים")
    rows = VW.sector_intel(uni, mkt) if uni else []
    if not rows:
        st.info("הסריקה הרחבה עדיין לא רצה.")
    reco_he = {"Overweight": "הגדלת משקל", "Neutral": "ניטרלי", "Underweight": "הקטנת משקל"}
    reco_col = {"Overweight": POSITIVE, "Neutral": WARNING, "Underweight": NEGATIVE}
    for r in rows:
        rc = reco_col.get(r["reco"], MUTED)
        rs = r.get("rs")
        rs_s = (f"{'+' if rs >= 0 else ''}{rs}%" if isinstance(rs, (int, float)) else "—")
        st.markdown(f"<div class='mcard' style='border-right:4px solid {rc}'>"
                    f"<div style='font-size:19px;font-weight:800'>{r['sector_he']}</div>"
                    f"<div class='mstats'>ציון <b style='color:{score_color(r['sector_score'])}'>{_fmt(r['sector_score'])}</b> · "
                    f"מומנטום <b>{_fmt(r.get('momentum'))}</b> · חוזק יחסי <b>{rs_s}</b></div>"
                    f"<div class='mco'>{r['n']} הזדמנויות · מובילה: {r['top']}</div>"
                    f"<div style='color:{rc};font-weight:700;font-size:16px;margin-top:4px'>{reco_he.get(r['reco'], '')}</div>"
                    f"</div>", unsafe_allow_html=True)


def _alerts(alerts):
    st.markdown("#### מרכז התראות")
    if not alerts:
        st.info("אין התראות.")
    sev_ord = {"גבוהה": 0, "בינונית": 1, "מידע": 2}
    sev_ic = {"גבוהה": ("🔴", NEGATIVE), "בינונית": ("🟠", "#fb923c"), "מידע": ("🔵", PRIMARY)}
    for i, a in enumerate(sorted(alerts, key=lambda x: sev_ord.get(x.get("severity"), 9))[:25]):
        ic, col = sev_ic.get(a.get("severity"), ("⚪", MUTED))
        tk = a.get("scope") or (re.match(r"^([A-Z][A-Z0-9.\-]{0,5})\b", a.get("message", "")) or [None, None])[1]
        st.markdown(f"<div class='mcard' style='border-right:4px solid {col}'>"
                    f"<div style='font-size:17px;font-weight:700'>{ic} {a['type']}"
                    + (f" · {tk}" if tk else "") + "</div>"
                    f"<div class='mco'>{a['message']}</div></div>", unsafe_allow_html=True)
        if tk and re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,5}", str(tk)):
            _goto("🔎 ניתוח", tk, key=f"al_{i}_{tk}", label=f"פתח ניתוח · {tk}")


def _settings(df, mkt, sysh):
    st.markdown("#### הגדרות ועוד")
    st.markdown(_grid([
        _mkpi("🔢", sysh.get("scanned", "—"), "נסרקו", "מניות", PRIMARY),
        _mkpi("🛡️", _fmt(sysh.get("avg_trust")), "אמון ממוצע", "מערכת", score_color(sysh.get("avg_trust"))),
    ]), unsafe_allow_html=True)
    st.markdown(f"<div class='mcard'><div class='mco'>עודכן לאחרונה: <b>{mkt.get('date', '—')}</b> · "
                f"{len(df)} מניות · מקור: Yahoo Finance</div>"
                f"<div class='mco'>פלטפורמה מבוססת-נתונים, ללא AI/LLM — כל מסקנה נגזרת ממדדים "
                f"מחושבים וניתנת לשחזור.</div></div>", unsafe_allow_html=True)
    if st.button("🖥️ עבור לתצוגת מחשב"):
        st.query_params["m"] = "0"
        st.rerun()


# ---------------------------------------------------------------------------

def _analysis(mkt, lookup, nc):
    """Mobile Company Analysis: header → Investment Decision → collapsed sections."""
    import deepdive
    from deepdive_report import to_html
    st.markdown("#### ניתוח חברה")
    st.session_state.setdefault("dd_ticker", "AAPL")
    tk = st.text_input("סימול", key="dd_ticker", placeholder="NVDA, AAPL, LLY").strip().upper()
    if not tk:
        return
    with st.spinner(f"מנתח את {tk}…"):
        try:
            bundle = _dd_fetch(tk)
            rep = deepdive.analyze(tk, sectors=mkt.get("sectors"), bundle=bundle)
        except Exception as e:
            rep = {"error": f"שגיאה בניתוח {tk}: {e}"}
    if rep.get("error"):
        st.error(rep["error"])
        return
    o, md, sc, rk = rep["overview"], rep["market_data"], rep["scores"], rep["risk"]
    fin, val = rep["financials"], rep["valuation"]
    hist, mkt_close = bundle.get("hist"), bundle.get("mkt_close")
    chg = md["daily_change"]
    chg_c = POSITIVE if not str(chg).startswith("-") else NEGATIVE
    _dec_fn = getattr(deepdive, "investment_decision", None)
    dec = _dec_fn(rep, regime_score=(mkt.get("regime") or {}).get("score")) if _dec_fn else None

    # --- Header: ticker, name, price, change, recommendation ---
    reco = (dec or {}).get("recommendation") or rep["opinion"].get("recommendation", "—")
    reco_he = reco.split("·")[-1].strip() if isinstance(reco, str) else "—"
    reco_c = (POSITIVE if "Buy" in str(reco) else NEGATIVE if ("Avoid" in str(reco) or "Reduce" in str(reco))
              else WARNING)
    st.markdown(f"<div class='mcard'>"
                f"<div><span class='mtick'>{tk}</span>"
                f"<span class='mrec' style='color:{reco_c}'>{reco_he}</span></div>"
                f"<div class='mco'>{o['name']} · {o['sector_he']}</div>"
                f"<div style='display:flex;align-items:baseline;gap:12px;margin-top:6px'>"
                f"<span class='big'>{md['price']}</span>"
                f"<span style='color:{chg_c};font-size:17px;font-weight:700'>{chg} היום</span></div>"
                f"</div>", unsafe_allow_html=True)

    # --- Investment Decision card (the one open section) ---
    if dec:
        ent = dec["entry"]
        ent_c = {"excellent": POSITIVE, "good": POSITIVE, "wait": WARNING,
                 "extended": "#fb923c", "avoid": NEGATIVE}.get(ent["band"], MUTED)
        conf = dec.get("confidence")
        rr_c = {"מצוין": POSITIVE, "טוב": POSITIVE, "סביר": WARNING, "חלש": NEGATIVE}.get(dec.get("rr_interpretation"), MUTED)
        st.markdown(
            f"<div class='mcard' style='border-right:4px solid {PRIMARY}'>"
            f"<div style='font-size:20px;font-weight:700;margin-bottom:8px'>החלטת השקעה</div>"
            f"<div class='mstats'>איכות כניסה: <b style='color:{ent_c}'>{ent['emoji']} {ent['label']}</b></div>"
            f"<div class='mco'>{' · '.join(ent['reasons'][:2])}</div>"
            f"<div class='mstats' style='margin-top:8px'>ביטחון <b style='color:{score_color(conf)}'>"
            f"{int(conf) if isinstance(conf, (int, float)) else '—'}%</b> · אופק <b>{dec['horizon']}</b></div>"
            + _grid([
                _mkpi("🎯", dec.get("target", "—"), "מחיר יעד", "קונצנזוס אנליסטים", PRIMARY),
                _mkpi("⚖️", dec.get("rr") if dec.get("rr") is not None else "—", "סיכון/סיכוי",
                      dec.get("rr_interpretation") or "", rr_c),
                _mkpi("🟢", f"${_fmt(dec.get('support'))}" if dec.get("support") else "—", "תמיכה",
                      _fmt(dec.get("downside"), "%"), POSITIVE),
                _mkpi("🔴", f"${_fmt(dec.get('resistance'))}" if dec.get("resistance") else "—", "התנגדות",
                      "", NEGATIVE),
            ]) + "</div>", unsafe_allow_html=True)

    # --- Collapsed sections (lazy content, charts behind a toggle) ---
    with st.expander("ביצועים"):
        chips = []
        for lbl, v in [("שבוע", md["ret_1w"]), ("חודש", md["ret_1m"]), ("3ח'", md["ret_3m"]),
                       ("6ח'", md["ret_6m"]), ("YTD", md["ytd"]), ("שנה", md["ret_1y"]), ("3ש'", md["ret_3y"])]:
            neg = str(v).startswith("-")
            col = MUTED if v == "אין נתון זמין" else (NEGATIVE if neg else POSITIVE)
            chips.append(f"<span class='chip' style='color:{col}'>{lbl} {v if v != 'אין נתון זמין' else '—'}</span>")
        st.markdown(f"<div class='chiprow'>{''.join(chips)}</div>", unsafe_allow_html=True)
        per = st.radio("תקופה", ["1W", "1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "MAX"],
                       index=5, horizontal=True, key="m_perf")
        perf = None
        _pf = getattr(ta, "performance", None)
        if hist is not None and _pf is not None:
            try:
                perf = _pf(hist["Close"], mkt_close, period=per)
            except Exception:
                perf = None
        if perf:
            scl = POSITIVE if perf["stock"] >= 0 else NEGATIVE
            st.markdown(f"<div class='mcard'><div class='mco'>תשואה · {per}</div>"
                        f"<div class='big' style='color:{scl}'>{perf['stock']:+.1f}%</div>"
                        f"<div class='mco'>S&P {_fmt(perf['bench'])}% · Alpha {_fmt(perf['alpha'])}% · "
                        f"CAGR {_fmt(perf['cagr'])}% · Sharpe {_fmt(perf['sharpe'])}</div></div>",
                        unsafe_allow_html=True)
        else:
            st.caption("נתוני ביצועים אינם זמינים כרגע.")

    with st.expander("גרפים"):
        if st.toggle("הצג גרף מחיר", key="m_chart"):
            mas = st.multiselect("ממוצעים נעים", ["MA20", "MA50", "MA200"], default=["MA50"], key="m_mas")
            c = hist["Close"].dropna().tail(252) if hist is not None else None
            if c is not None and len(c) > 2:
                fig = go.Figure(go.Scatter(y=c.values, x=c.index, name="מחיר", line_color=PRIMARY,
                                           fill="tozeroy", fillcolor="rgba(94,168,255,0.10)"))
                for nm_, col_ in [("MA20", "#FBBF24"), ("MA50", "#B388FF"), ("MA200", "#F1F5F9")]:
                    n_ = int(nm_[2:])
                    if nm_ in mas and len(c) >= n_:
                        fig.add_trace(go.Scatter(y=c.rolling(n_).mean().values, x=c.index,
                                                 name=nm_, line=dict(width=1.3, color=col_)))
                srl0 = (rep.get("technicals") or {}).get("sr_levels") or {}
                if srl0.get("support"):
                    fig.add_hline(y=srl0["support"], line_dash="dot", line_color=POSITIVE)
                if srl0.get("resistance"):
                    fig.add_hline(y=srl0["resistance"], line_dash="dot", line_color=NEGATIVE)
                fig.update_layout(title=f"{tk} · שנה", showlegend=False)
                fig.update_xaxes(tickformat="%d/%m/%y", hoverformat="%d/%m/%Y",
                                 rangebreaks=[dict(bounds=["sat", "mon"])])
                st.plotly_chart(style_fig(fig, 280), use_container_width=True)

    with st.expander("ניתוח טכני"):
        tech = rep["technicals"]
        st.markdown(f"<div class='mco'>מגמה: <b>{tech['trend']}</b> · מומנטום: <b>{tech['momentum']}</b> · "
                    f"RSI: <b>{tech['rsi']}</b></div>", unsafe_allow_html=True)
        tsub = tech.get("sub_scores") or {}
        st.markdown("<div class='mcard'>" + score_bar("מגמה", tsub.get("trend"))
                    + score_bar("מומנטום", tsub.get("momentum")) + score_bar("נפח", tsub.get("volume"))
                    + "</div>", unsafe_allow_html=True)
        srl = tech.get("sr_levels")
        if srl:
            st.markdown(f"<div class='mco'>{srl.get('interpretation', '')}</div>", unsafe_allow_html=True)

    with st.expander("פונדמנטלי"):
        for k, vv in [("הכנסות", fin["revenue"]), ("צמיחת הכנסות", fin["revenue_growth"]),
                      ("שולי תפעול", fin["operating_margin"]), ("רווח למניה", fin["eps"]),
                      ("תזרים חופשי", fin["fcf"]), ("חוב/הון", fin["debt_to_equity"]),
                      ("ROIC", fin["roic"])]:
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:9px 2px;"
                        f"border-bottom:1px solid {BORDER};font-size:16px'>"
                        f"<span style='color:{SECONDARY}'>{k}</span><b>{vv}</b></div>", unsafe_allow_html=True)

    with st.expander("תמחור"):
        for k, vv in [("מכפיל עתידי", val["forward_pe"]), ("PEG", val["peg"]),
                      ("מחיר/מכירות", val["price_sales"]), ("EV/EBITDA", val["ev_ebitda"])]:
            st.markdown(f"<div style='display:flex;justify-content:space-between;padding:9px 2px;"
                        f"border-bottom:1px solid {BORDER};font-size:16px'>"
                        f"<span style='color:{SECONDARY}'>{k}</span><b>{vv}</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-weight:700;margin-top:10px;font-size:17px;"
                    f"color:{score_color(val.get('score'))}'>{val['label']}</div>", unsafe_allow_html=True)

    with st.expander("סיכונים"):
        st.markdown(f"<div class='mco'>ביתא {rk['beta']} · תנודתיות {rk['volatility']}% · "
                    f"ירידה מקס׳ {rk['max_drawdown']}% · ציון סיכון <b>{rk['risk_score']}</b> ({rk['category']})</div>",
                    unsafe_allow_html=True)
        for x in (dec or {}).get("risks", []):
            st.markdown(f"<div class='mco'>• {x}</div>", unsafe_allow_html=True)

    with st.expander("תזה — תרחישים"):
        sty = {"bull": "#22c55e", "base": "#38bdf8", "bear": "#ef4444"}
        for s in rep.get("scenarios", []):
            ac = sty.get(s["key"], PRIMARY)
            up = s["target"].get("upside")
            pill = (f"<span style='color:{POSITIVE if up >= 0 else NEGATIVE};font-weight:700'>"
                    f"{'+' if up >= 0 else ''}{up}%</span>") if up is not None else ""
            st.markdown(f"<div class='mcard' style='border-right:4px solid {ac}'>"
                        f"<b style='color:{ac};font-size:17px'>{s['emoji']} {s['title']}</b> · סבירות {s['prob']}%<br>"
                        f"<span class='mco'>יעד {s['target']['price']} {pill}</span>"
                        f"<div class='mwhy' style='margin-top:6px'>{s['summary']}</div></div>",
                        unsafe_allow_html=True)

    st.download_button("📥 הורד דוח HTML", data=to_html(rep), file_name=f"deepdive_{tk}.html",
                       mime="text/html", use_container_width=True)
    _goto("💎 הזדמנויות", key="back_opp", label="חזור להזדמנויות")
