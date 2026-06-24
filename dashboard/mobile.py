# -*- coding: utf-8 -*-
"""Mobile-first UI (Phase 16 + mobile-adaptation Route A).

Separate from the desktop dashboard; rendered when the app detects a narrow
screen (or ?m=1). Card-based, touch-friendly, RTL, no wide tables. Session-state
driven navigation (pills) so cards can deep-link into the mobile Company Analysis
screen. Reuses the same engines + artifacts as desktop (no scoring changes).
"""
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import market
import technicals as ta
from ranking_engine.interpret import classify
from ranking_engine.score import score_stock
from dashboard import views as VW
from dashboard.theme import (GREEN, AMBER, RED, BLUE, CARD, MUTED, TEXT, PRIMARY, POSITIVE,
                             WARNING, NEGATIVE, SECONDARY, score_color, score_bar, style_fig)

MOBILE_CSS = f"""
<style>
  .stApp {{ background:#08111f; }}
  section[data-testid="stSidebar"] {{ display:none; }}
  .block-container {{ padding:0.6rem 0.7rem 4rem !important; max-width:100% !important; }}
  html, body, .stApp {{ overflow-x:hidden; }}
  * {{ direction:rtl; }}
  h1,h2,h3,h4,p,div,span,li {{ text-align:right; color:{TEXT}; }}
  .sticky {{ position:sticky; top:0; z-index:99; background:#0b1220; border-bottom:1px solid #233456;
            padding:10px 12px; margin:-0.6rem -0.7rem 8px; font-size:15px; }}
  .mcard {{ background:#0f1f3d; border:1px solid #233456; border-radius:14px; padding:13px 15px;
            margin:9px 0; box-shadow:0 2px 6px rgba(0,0,0,.3); }}
  .mtick {{ font-size:20px; font-weight:800; }}
  .mrec {{ font-size:14px; font-weight:700; float:left; }}
  .mco {{ color:{SECONDARY}; font-size:13px; margin:2px 0; line-height:1.5; }}
  .mstats {{ font-size:14px; margin:7px 0; }}
  .mwhy {{ color:{SECONDARY}; font-size:13px; line-height:1.6; }}
  .big {{ font-size:30px; font-weight:800; }}
  .stButton button {{ min-height:46px; font-size:16px; border-radius:10px; width:100%; }}
  div[data-testid="stMetricValue"] {{ font-size:1.5rem; }}
  /* nav pills */
  div[data-testid="stRadio"] [role="radiogroup"] {{ flex-wrap:nowrap; overflow-x:auto; gap:6px; }}
  div[data-testid="stRadio"] [role="radiogroup"] label {{ background:#16284d; border:1px solid #233456;
       border-radius:999px; padding:6px 12px; white-space:nowrap; font-size:14px; font-weight:700; }}
  .kpi-grid {{ grid-template-columns:repeat(2,1fr) !important; }}
  .scen {{ margin-bottom:10px; }}
</style>
"""


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


def _mkpi(ico, val, lab, sub, ac):
    return (f"<div class='kpi' style='--ac:{ac}'><div class='k-ico'>{ico}</div>"
            f"<div class='k-val' style='font-size:26px'>{val}</div>"
            f"<div class='k-lab'>{lab}</div><div class='k-sub'>{sub}</div></div>")


def _grid(cards, cols=2):
    return f"<div class='kpi-grid' style='grid-template-columns:repeat({cols},1fr)'>{''.join(cards)}</div>"


def _opp_card(r, lookup, nc):
    info = classify(r)
    tk = r["Ticker"]
    nm = VW.company_name(tk, lookup, nc)
    chg = r.get("DailyChange%", 0) or 0
    ccol = POSITIVE if chg >= 0 else NEGATIVE
    sv = _num(r.get("ScoreV2", r.get("Score")))
    rb = VW.risk_badge(r.get("RiskLevel"))
    st.markdown(
        f"""<div class="mcard" style="border-right:6px solid {info['color']}">
          <div><span class="mtick">{tk}</span>
            <span class="mrec" style="color:{info['color']}">{info['emoji']} {info['label']}</span></div>
          <div class="mco">{nm}</div>
          <div class="mstats">ציון V2 <b>{int(sv) if sv is not None else '—'}</b> ·
            <span style="color:{rb[3]}">{rb[0]} {rb[1]}</span> ·
            <span style="color:{ccol}">{'+' if chg >= 0 else ''}{chg}%</span></div>
          <div class="mwhy">{info['summary']}</div>
        </div>""", unsafe_allow_html=True)
    if st.button(f"🔎 ניתוח {tk}", key=f"man_{tk}", use_container_width=True):
        st.session_state["dd_ticker"] = tk
        st.session_state["_m_pending"] = "🔎 ניתוח"
        st.rerun()


# ---------------------------------------------------------------------------

def render(df, mkt):
    """Entry point: render the full mobile experience (session-nav driven)."""
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
                f"<b style='color:{rcol}'>{reg_s}</b> ({regime.get('label', '')}) · "
                f"פחד/חמדנות {fng.get('score', '—')}</div>", unsafe_allow_html=True)

    PAGES = ["🏠 בית", "💎 הזדמנויות", "🔎 ניתוח", "🗺️ סקטורים", "🔔 התראות", "📊 שוק", "⚙️"]
    if st.session_state.get("_m_pending"):
        st.session_state["m_page"] = st.session_state.pop("_m_pending")
    page = st.radio("ניווט", PAGES, horizontal=True, key="m_page", label_visibility="collapsed")

    pos = df[df["_g"] == "positive"].sort_values("ScoreV2", ascending=False)

    # ---------------- HOME ----------------
    if page == "🏠 בית":
        crit = [a for a in alerts if a.get("severity") == "גבוהה"]
        tr = sysh.get("avg_trust")
        fg = fng.get("score")
        fgc = NEGATIVE if isinstance(fg, (int, float)) and fg < 45 else POSITIVE if isinstance(fg, (int, float)) and fg > 55 else WARNING
        st.markdown(_grid([
            _mkpi("🧭", _fmt(reg_s), "מצב שוק", regime.get("label", ""), rcol),
            _mkpi("😶‍🌫️", _fmt(fg), "פחד/חמדנות", fng.get("label", ""), fgc),
            _mkpi("💎", len(pos), "הזדמנויות", "סטטוס חיובי", POSITIVE),
            _mkpi("🔔", len(crit), "התראות קריטיות", f"מתוך {len(alerts)}", NEGATIVE if crit else MUTED),
        ]), unsafe_allow_html=True)
        st.markdown("#### 💎 3 ההזדמנויות המובילות")
        for _, r in (pos if not pos.empty else df.sort_values("ScoreV2", ascending=False)).head(3).iterrows():
            _opp_card(r, lookup, nc)
        if sectors:
            s, w = sectors[0], sectors[-1]
            st.markdown(_grid([
                _mkpi("🟢", s["sector"], "סקטור חזק", f"ציון {s['score']}", POSITIVE),
                _mkpi("🔴", w["sector"], "סקטור חלש", f"ציון {w['score']}", NEGATIVE),
            ]), unsafe_allow_html=True)
        if crit[:3]:
            st.markdown("#### 🔔 התראות קריטיות")
            for a in crit[:3]:
                st.markdown(f"<div class='mcard' style='border-right:6px solid {NEGATIVE};padding:10px 14px'>"
                            f"<b>{a['type']}</b> · {a['message']}</div>", unsafe_allow_html=True)

    # ---------------- OPPORTUNITIES ----------------
    elif page == "💎 הזדמנויות":
        base = pos if not pos.empty else df.sort_values("ScoreV2", ascending=False)
        with st.expander("⚙️ סינון מתקדם"):
            secs = sorted([s for s in df.get("Sector", pd.Series()).dropna().unique()])
            f_sec = st.selectbox("סקטור", ["הכל"] + secs, key="m_sec")
            f_risk = st.multiselect("רמת סיכון", ["נמוך", "בינוני", "גבוה", "גבוה מאוד"], key="m_risk")
            SC = {"הכל": 0, "60+": 60, "70+": 70, "80+": 80}
            f_score = SC[st.selectbox("ציון מינימלי (Score V2)", list(SC), key="m_score")]
        v = base
        if f_sec != "הכל" and "Sector" in v:
            v = v[v["Sector"] == f_sec]
        if f_risk:
            v = v[v["RiskLevel"].isin(f_risk)]
        v = v[v["ScoreV2"].fillna(0) >= f_score]
        st.markdown(f"**נמצאו {len(v)} מניות**")
        if v.empty:
            st.info("אין מניות שעוברות את הסינון. נסה להרחיב את התנאים.")
        for _, r in v.head(25).iterrows():
            _opp_card(r, lookup, nc)

    # ---------------- COMPANY ANALYSIS ----------------
    elif page == "🔎 ניתוח":
        _analysis(mkt, lookup, nc)

    # ---------------- SECTORS ----------------
    elif page == "🗺️ סקטורים":
        st.markdown("#### 🗺️ סקטורים")
        rows = VW.sector_intel(uni, mkt) if uni else []
        if not rows:
            st.info("הסריקה הרחבה עדיין לא רצה.")
        reco_he = {"Overweight": "הגדלת משקל", "Neutral": "ניטרלי", "Underweight": "הקטנת משקל"}
        reco_col = {"Overweight": POSITIVE, "Neutral": WARNING, "Underweight": NEGATIVE}
        for r in rows:
            rc = reco_col.get(r["reco"], MUTED)
            top = r["top"] + ("" if r["top_name"] == r["top"] else f" · {r['top_name']}")
            st.markdown(f"<div class='mcard' style='border-right:6px solid {rc}'>"
                        f"<div style='font-size:16px;font-weight:800'>{r['sector_he']}</div>"
                        f"<div class='mco'>{r['n']} הזדמנויות · ScoreV2 ממוצע <b>{_fmt(r['avg_score'])}</b></div>"
                        f"<div class='mco'>מובילה: {top}</div>"
                        f"<div style='color:{rc};font-weight:700;margin-top:4px'>{reco_he.get(r['reco'], '')}</div>"
                        f"</div>", unsafe_allow_html=True)

    # ---------------- ALERTS ----------------
    elif page == "🔔 התראות":
        st.markdown("#### 🔔 מרכז התראות")
        if not alerts:
            st.info("אין התראות.")
        sev_col = {"גבוהה": NEGATIVE, "בינונית": WARNING, "מידע": PRIMARY}
        for a in alerts[:25]:
            col = sev_col.get(a.get("severity"), MUTED)
            st.markdown(f"<div class='mcard' style='border-right:6px solid {col};padding:10px 14px'>"
                        f"<b>{a['type']}</b> · <span style='color:{col}'>{a['severity']}</span><br>"
                        f"{a['message']}</div>", unsafe_allow_html=True)

    # ---------------- MARKET INTELLIGENCE ----------------
    elif page == "📊 שוק":
        st.markdown("#### 📊 אינטליגנציית שוק")
        st.markdown(_grid([
            _mkpi("🔢", sysh.get("scanned", "—"), "נסרקו", "מניות", PRIMARY),
            _mkpi("✅", _fmt(sysh.get("data_completeness"), "%"), "שלמות נתונים", "", POSITIVE),
            _mkpi("🛡️", _fmt(sysh.get("avg_trust")), "אמון ממוצע", "מערכת", score_color(sysh.get("avg_trust"))),
            _mkpi("⚠️", sysh.get("failed_pulls", "—"), "משיכות שנכשלו", "", WARNING),
        ]), unsafe_allow_html=True)
        st.markdown("##### מניות מדורגות (Top)")
        for _, r in df.sort_values("ScoreV2", ascending=False).head(15).iterrows():
            sv = _num(r.get("ScoreV2"))
            st.markdown(f"<div class='mcard' style='padding:9px 13px'>"
                        f"<b>{r['Ticker']}</b> <span class='mco'>{VW.company_name(r['Ticker'], lookup, nc)}</span>"
                        f"<span style='float:left;color:{score_color(sv)};font-weight:800'>V2 {int(sv) if sv is not None else '—'}</span>"
                        f"</div>", unsafe_allow_html=True)

    # ---------------- SETTINGS ----------------
    elif page == "⚙️":
        st.markdown("#### ⚙️ הגדרות")
        st.markdown(f"<div class='mcard'><div class='mco'>עודכן לאחרונה: <b>{mkt.get('date', '—')}</b></div>"
                    f"<div class='mco'>{len(df)} מניות · מקור: Yahoo Finance</div></div>", unsafe_allow_html=True)
        if st.button("🔄 רענן נתונים עכשיו"):
            import subprocess
            import sys
            with st.spinner("מריץ סריקה…"):
                try:
                    subprocess.run([sys.executable, "run.py"],
                                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   timeout=300, env=dict(os.environ, STOCK_AGENT_DISABLE_EMAIL="1", PYTHONUTF8="1"),
                                   capture_output=True, text=True)
                    st.cache_data.clear()
                    st.success("עודכן!")
                    st.rerun()
                except Exception:
                    st.error("הרענון נכשל.")
        st.markdown(f"<div class='mcard'><div style='font-weight:800;margin-bottom:4px'>ℹ️ אודות</div>"
                    f"<div class='mco'>Stock Agent — פלטפורמת אינטליגנציה מבוססת-נתונים. ללא AI/LLM. "
                    f"כל מסקנה נגזרת מנתונים ומנועי ניקוד דטרמיניסטיים.</div></div>", unsafe_allow_html=True)

    st.divider()
    if st.button("🖥️ עבור לתצוגת מחשב"):
        st.query_params["m"] = "0"
        st.rerun()
    st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")


def _analysis(mkt, lookup, nc):
    """Mobile Company Analysis — condensed deep-dive (reuses deepdive engine)."""
    import deepdive
    from deepdive_report import to_html
    st.markdown("#### 🔎 ניתוח חברה")
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
    hist, mkt_close = bundle.get("hist"), bundle.get("mkt_close")

    desc = o.get("summary_he") or o.get("he_line") or ""
    st.markdown(f"<div class='mcard'><div style='font-size:20px;font-weight:800'>{o['name']} "
                f"<span class='mco'>· {tk}</span></div>"
                f"<div class='mco'>{o['sector_he']} · {o['industry']}</div>"
                f"<div style='font-size:15px;line-height:1.8;margin-top:8px'>{desc}</div></div>",
                unsafe_allow_html=True)

    v2 = sc["final_v2"]["value"]
    st.markdown(_grid([
        _mkpi("💵", md["price"], "מחיר", md["daily_change"], PRIMARY),
        _mkpi("🎯", v2, "Score V2", "משוקלל", score_color(v2)),
        _mkpi("🛡️", sc["trust"]["value"], "אמון", sc["trust"]["category"], score_color(sc["trust"]["value"])),
        _mkpi("⚠️", rk["risk_score"], "סיכון", rk["category"],
              NEGATIVE if (rk["risk_score"] or 0) >= 66 else WARNING if (rk["risk_score"] or 0) >= 33 else POSITIVE),
    ]), unsafe_allow_html=True)

    # performance (guarded — survive a stale/missing technicals module on the cloud)
    per = st.selectbox("תקופה", ["1W", "1M", "3M", "6M", "YTD", "1Y", "3Y", "MAX"], index=5, key="m_perf")
    perf = None
    _perf_fn = getattr(ta, "performance", None)
    if hist is not None and _perf_fn is not None:
        try:
            perf = _perf_fn(hist["Close"], mkt_close, period=per)
        except Exception:
            perf = None
    if perf is None:
        st.caption("נתוני ביצועים אינם זמינים כרגע (נסה לרענן את הדף).")
    if perf:
        scl = POSITIVE if perf["stock"] >= 0 else NEGATIVE
        alpha = perf["alpha"]
        ins = ("🟢 היכתה את S&P" if (alpha or 0) >= 2 else "🔴 פיגרה אחרי S&P" if (alpha or 0) <= -2
               else "🟡 דומה ל-S&P") if alpha is not None else ""
        st.markdown(f"<div class='mcard'><div class='mco'>תשואה · {per}</div>"
                    f"<div class='big' style='color:{scl}'>{perf['stock']:+.1f}%</div>"
                    f"<div class='mco'>S&P {_fmt(perf['bench'])}% · Alpha {_fmt(perf['alpha'])}% · {ins}</div></div>",
                    unsafe_allow_html=True)
        st.markdown(_grid([
            _mkpi("📈", _fmt(perf["cagr"], "%"), "CAGR", "", PRIMARY),
            _mkpi("〰️", _fmt(perf["vol"], "%"), "תנודתיות", "", WARNING),
            _mkpi("📉", _fmt(perf["maxdd"], "%"), "ירידה מקס׳", "", NEGATIVE),
            _mkpi("⚖️", _fmt(perf["sharpe"]), "Sharpe", "", PRIMARY),
        ]), unsafe_allow_html=True)
        if hist is not None:
            c = hist["Close"].dropna()
            c = c[(c.index >= perf["start"]) & (c.index <= perf["end"])]
            fig = go.Figure(go.Scatter(y=c.values, x=list(range(len(c))), line_color=PRIMARY,
                                       fill="tozeroy", fillcolor="rgba(0,194,255,0.10)"))
            fig.update_layout(title=f"{tk} · {per}")
            st.plotly_chart(style_fig(fig, 200), use_container_width=True)

    # score bars
    rh = sc["risk"]["value"]
    st.markdown("##### 🎯 ציונים")
    st.markdown("<div class='mcard'>" + score_bar("ציון סופי v2", v2)
                + score_bar("טכני", sc["technical"]["value"])
                + score_bar("פונדמנטלי", _num(sc["fundamental"]["value"]))
                + score_bar("אמון", sc["trust"]["value"])
                + score_bar("ניהול סיכון", (None if not isinstance(rh, (int, float)) else 100 - rh))
                + "</div>", unsafe_allow_html=True)

    # scenarios
    st.markdown("##### 🧠 תרחישים")
    sty = {"bull": ("#22c55e", "rgba(34,197,94,0.10)"), "base": ("#38bdf8", "rgba(56,189,248,0.10)"),
           "bear": ("#ef4444", "rgba(239,68,68,0.10)")}
    for s in rep.get("scenarios", []):
        ac, bg = sty.get(s["key"], (PRIMARY, "rgba(56,189,248,0.10)"))
        up = s["target"].get("upside")
        pill = (f"<span style='color:{POSITIVE if up >= 0 else NEGATIVE}'>"
                f"{'+' if up >= 0 else ''}{up}%</span>") if up is not None else ""
        st.markdown(f"<div class='mcard' style='border-right:6px solid {ac}'>"
                    f"<b style='color:{ac};font-size:16px'>{s['emoji']} {s['title']}</b> · סבירות {s['prob']}%<br>"
                    f"<span class='mco'>יעד {s['target']['price']} {pill}</span>"
                    f"<div class='mwhy' style='margin-top:6px'>{s['summary']}</div></div>", unsafe_allow_html=True)

    op = rep["opinion"]
    st.markdown(f"<div class='mcard' style='border-right:6px solid {PRIMARY}'>"
                f"<div style='font-size:20px;font-weight:800;color:{PRIMARY}'>{op['recommendation']}</div>"
                f"<div class='mco' style='margin-top:4px'>{op['attractive']}</div>"
                f"<div class='mco'>הקצאה מוצעת: <b>{op['allocation_pct']}%</b></div></div>", unsafe_allow_html=True)
    st.download_button("📥 הורד דוח HTML", data=to_html(rep), file_name=f"deepdive_{tk}.html", mime="text/html")
