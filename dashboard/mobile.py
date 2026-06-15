# -*- coding: utf-8 -*-
"""Mobile-first UI (Phase 16). Separate from the desktop dashboard.

Rendered only when the app detects a narrow screen (or ?m=1). Card-based,
touch-friendly, RTL, no wide tables/radars. Reads the same precomputed
artifacts as desktop. Goal: understand the market + your actions in 30 seconds.
"""
import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import market
from ranking_engine.interpret import classify
from dashboard.theme import GREEN, AMBER, RED, BLUE, CARD, MUTED, TEXT

MOBILE_CSS = f"""
<style>
  .stApp {{ background:#0e1726; }}
  /* hide desktop sidebar on mobile */
  section[data-testid="stSidebar"] {{ display:none; }}
  .block-container {{ padding:0.6rem 0.7rem 4rem !important; max-width:100% !important; }}
  html, body, .stApp {{ overflow-x:hidden; }}
  * {{ direction:rtl; }}
  h1,h2,h3,h4,p,div,span {{ text-align:right; color:{TEXT}; }}

  .sticky {{ position:sticky; top:0; z-index:99; background:#0b1220;
            border-bottom:1px solid #233456; padding:10px 12px; margin:-0.6rem -0.7rem 10px;
            font-size:15px; }}
  .mcard {{ background:{CARD}; border:1px solid #233456; border-radius:14px;
            padding:14px 16px; margin:10px 0; box-shadow:0 2px 6px rgba(0,0,0,.3); }}
  .mtick {{ font-size:20px; font-weight:800; }}
  .mrec {{ font-size:15px; font-weight:700; float:left; }}
  .mco {{ color:{MUTED}; font-size:13px; margin:2px 0; }}
  .mstats {{ font-size:15px; margin:8px 0; }}
  .mwhy {{ color:{MUTED}; font-size:13px; line-height:1.6; }}
  .big {{ font-size:30px; font-weight:800; }}
  /* touch-friendly tabs + buttons */
  .stTabs [data-baseweb="tab-list"] {{ gap:6px; direction:rtl; overflow-x:auto; }}
  .stTabs [data-baseweb="tab"] {{ font-size:15px; padding:10px 12px; }}
  .stButton button {{ min-height:46px; font-size:16px; border-radius:10px; width:100%; }}
  div[data-testid="stMetricValue"] {{ font-size:1.5rem; }}
</style>
"""


def _fmt(v, suf="", dash="—"):
    if v is None or (isinstance(v, float) and v != v):
        return dash
    return f"{v}{suf}"


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return default
    return default


def _opp_card(r):
    info = classify(r)
    chg = r.get("DailyChange%", 0) or 0
    ccol = GREEN if chg >= 0 else RED
    st.markdown(
        f"""<div class="mcard" style="border-right:6px solid {info['color']}">
          <div><span class="mtick">{r['Ticker']}</span>
            <span class="mrec" style="color:{info['color']}">{info['emoji']} {info['label']}</span></div>
          <div class="mco">{r['Name']}</div>
          <div class="mstats">ציון <b>{int(r.get('ScoreV2', r.get('Score', 0)))}</b> ·
            אמון <b>{_fmt(int(r['TrustScore']) if r.get('TrustScore') == r.get('TrustScore') else None)}</b> ·
            סיכון {_fmt(r.get('RiskLevel'))} ·
            <span style="color:{ccol}">{'+' if chg >= 0 else ''}{chg}%</span></div>
          <div class="mwhy">{info['summary']}</div>
        </div>""", unsafe_allow_html=True)


def render(df, mkt):
    """Entry point: render the full mobile experience."""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    pf = _load(config.PORTFOLIO_JSON, {})
    alerts = _load(config.ALERTS_CENTER_JSON, [])

    df = df.copy()
    df["_g"] = [classify(r)["group"] for _, r in df.iterrows()]
    regime = mkt.get("regime", {})
    fng = mkt.get("fear_greed", {})
    sectors = sorted(mkt.get("sectors", []), key=lambda s: -s.get("score", 0))

    # Sticky top summary
    reg_s = regime.get("score", "—")
    rcol = GREEN if isinstance(reg_s, (int, float)) and reg_s >= 60 else \
        (RED if isinstance(reg_s, (int, float)) and reg_s < 40 else AMBER)
    st.markdown(
        f"<div class='sticky'>🤖 <b>Stock Agent</b> · מצב שוק "
        f"<b style='color:{rcol}'>{reg_s}</b> ({regime.get('label', '')}) · "
        f"פחד/חמדנות {fng.get('score', '—')}</div>", unsafe_allow_html=True)

    tabs = st.tabs(["🏠 בית", "💎 הזדמנויות", "💼 תיק", "🔔 התראות"])

    # ---------- HOME ----------
    with tabs[0]:
        st.markdown(f"<div class='mcard' style='border-right:6px solid {rcol}'>"
                    f"<div class='mco'>מצב שוק</div>"
                    f"<div class='big' style='color:{rcol}'>{reg_s} · {regime.get('label', '')}</div>"
                    f"</div>", unsafe_allow_html=True)

        # What should I do today?
        today = (pf.get("decisions", {}) or {}).get("today", [])
        st.markdown("#### ✅ מה לעשות היום?")
        if today:
            for a in today[:4]:
                st.markdown(f"<div class='mcard' style='padding:10px 14px'>{a}</div>",
                            unsafe_allow_html=True)
        else:
            st.caption("אין פעולות תיק. ראה הזדמנויות בלשונית 💎.")

        # Top 3 opportunities
        st.markdown("#### 💎 3 ההזדמנויות המובילות")
        pos = df[df["_g"] == "positive"].sort_values("ScoreV2", ascending=False)
        ranked = pos if not pos.empty else df.sort_values("ScoreV2", ascending=False)
        for _, r in ranked.head(3).iterrows():
            _opp_card(r)

        # Strongest / weakest sector
        if sectors:
            s, w = sectors[0], sectors[-1]
            cc = st.columns(2)
            cc[0].markdown(f"<div class='mcard' style='border-right:6px solid {GREEN}'>"
                           f"<div class='mco'>סקטור חזק</div><div style='font-size:17px;font-weight:800'>"
                           f"{s['sector']}</div><div>ציון {s['score']}</div></div>", unsafe_allow_html=True)
            cc[1].markdown(f"<div class='mcard' style='border-right:6px solid {RED}'>"
                           f"<div class='mco'>סקטור חלש</div><div style='font-size:17px;font-weight:800'>"
                           f"{w['sector']}</div><div>ציון {w['score']}</div></div>", unsafe_allow_html=True)

        # Portfolio health
        if not pf.get("empty") and pf.get("health"):
            h = pf["health"]["score"]
            hcol = GREEN if h >= 66 else (AMBER if h >= 40 else RED)
            st.markdown(f"<div class='mcard'><div class='mco'>בריאות תיק</div>"
                        f"<div class='big' style='color:{hcol}'>{h}/100</div></div>",
                        unsafe_allow_html=True)

        # Critical alerts (high severity)
        crit = [a for a in alerts if a.get("severity") == "גבוהה"][:3]
        if crit:
            st.markdown("#### 🔔 התראות קריטיות")
            for a in crit:
                st.markdown(f"<div class='mcard' style='border-right:6px solid {RED};padding:10px 14px'>"
                            f"<b>{a['type']}</b> · {a['message']}</div>", unsafe_allow_html=True)

    # ---------- OPPORTUNITIES ----------
    with tabs[1]:
        st.markdown("#### 💎 הזדמנויות")
        pos = df[df["_g"] == "positive"].sort_values("ScoreV2", ascending=False)
        shown = pos if not pos.empty else df.sort_values("ScoreV2", ascending=False).head(10)
        if shown.empty:
            st.caption("אין הזדמנויות חיוביות היום.")
        for _, r in shown.iterrows():
            _opp_card(r)

    # ---------- PORTFOLIO ----------
    with tabs[2]:
        st.markdown("#### 💼 תיק")
        if pf.get("empty") or not pf.get("positions"):
            st.caption("אין החזקות. ערוך portfolio.csv בגרסת המחשב.")
        else:
            cc = st.columns(2)
            cc[0].metric("שווי תיק", f"${pf['total_value']:,.0f}", f"{pf['total_pl_pct']:+.1f}%")
            cc[1].metric("שינוי יומי", f"{pf.get('daily_change_pct', 0):+.2f}%")
            # Top holding risk
            risky = max(pf["positions"], key=lambda p: {"נמוך": 0, "בינוני": 1, "גבוה": 2,
                                                        "גבוה מאוד": 3}.get(p.get("risk_level"), 0))
            st.markdown(f"<div class='mcard'><div class='mco'>סיכון ההחזקה הגדולה</div>"
                        f"<b>{risky['ticker']}</b> · {_fmt(risky.get('risk_level'))} · "
                        f"משקל {risky.get('weight', 0):.0f}%</div>", unsafe_allow_html=True)
            # Sector exposure warning
            warns = (pf.get("risk", {}) or {}).get("warnings", [])
            for w in warns[:2]:
                st.markdown(f"<div class='mcard' style='border-right:6px solid {AMBER};padding:10px 14px'>"
                            f"⚠️ {w}</div>", unsafe_allow_html=True)
            # Suggested action
            today = (pf.get("decisions", {}) or {}).get("today", [])
            if today:
                st.markdown("#### פעולה מוצעת")
                st.markdown(f"<div class='mcard' style='border-right:6px solid {BLUE};padding:10px 14px'>"
                            f"{today[0]}</div>", unsafe_allow_html=True)

    # ---------- ALERTS ----------
    with tabs[3]:
        st.markdown("#### 🔔 התראות")
        if not alerts:
            st.caption("אין התראות.")
        sev_col = {"גבוהה": RED, "בינונית": AMBER, "מידע": BLUE}
        for a in alerts[:20]:
            col = sev_col.get(a.get("severity"), MUTED)
            st.markdown(f"<div class='mcard' style='border-right:6px solid {col};padding:10px 14px'>"
                        f"<b>{a['type']}</b> · <span style='color:{col}'>{a['severity']}</span><br>"
                        f"{a['message']}</div>", unsafe_allow_html=True)

    st.divider()
    if st.button("🖥️ עבור לתצוגת מחשב"):
        st.query_params["m"] = "0"
        st.rerun()
    st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")
