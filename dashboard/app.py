# -*- coding: utf-8 -*-
"""Stock Agent Pro — professional investment-intelligence dashboard.

Loads PRECOMPUTED artifacts (results.csv, market_overview.json, closes.json)
written by run.py, so it opens instantly with ZERO live network calls. Every
panel is wired to real data; proprietary indicators are clearly labeled.
Hebrew / RTL throughout. No fabricated values (Phase 10: never NaN/None).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import config
import market
from config import COLUMN_LABELS_HE as L
from ranking_engine.interpret import classify
from ranking_engine.factor_scores import factor_scores
from ranking_engine.score import score_breakdown, COMPONENT_LABELS_HE
from news.headlines import get_headlines
from news.sentiment import score_headlines
from assistant import answer as assistant_answer
from explain import explain as explain_stock
import trust as trust_engine
from dashboard.theme import (DARK_CSS, style_fig, GREEN, AMBER, RED, BLUE, CARD, MUTED, TEXT,
                             PRIMARY, POSITIVE, WARNING, NEGATIVE, BG, BORDER, ELEV,
                             score_color, regime_color, sparkline_svg, score_bar)

st.set_page_config(page_title="Stock Agent Pro", page_icon="📈", layout="wide")
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ===========================================================================
# Data-quality helper (Phase 10) — never show NaN / None / empty
# ===========================================================================

def fmt(v, suffix="", dash="—"):
    """Format a value for display; returns a dash for missing data."""
    if v is None:
        return dash
    try:
        if isinstance(v, float) and (v != v):   # NaN
            return dash
    except Exception:
        pass
    return f"{v}{suffix}"


NA_ = "אין נתון זמין"


def _num_or(s):
    """Parse the leading number out of a formatted string (e.g. '+3.46%') → float|None."""
    import re
    if isinstance(s, (int, float)):
        return s if s == s else None
    m = re.search(r"-?\d+\.?\d*", str(s).replace(",", ""))
    return float(m.group()) if m else None


def _disp(v):
    """Display helper: None → 'אין נתון זמין'."""
    return NA_ if v is None else v


# ===========================================================================
# Cached loaders — read precomputed artifacts (instant, no network)
# ===========================================================================

@st.cache_data(ttl=120, show_spinner=False)
def load_results() -> pd.DataFrame:
    inv = {v: k for k, v in L.items()}
    df = pd.read_csv(config.RESULTS_CSV).rename(columns=inv)
    df["_group"] = [classify(r)["group"] for _, r in df.iterrows()]
    return df


@st.cache_data(ttl=120, show_spinner=False)
def load_market() -> dict:
    if os.path.exists(config.MARKET_JSON):
        with open(config.MARKET_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


@st.cache_data(ttl=120, show_spinner=False)
def load_closes() -> dict:
    if os.path.exists(config.CLOSES_JSON):
        with open(config.CLOSES_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


@st.cache_data(ttl=120, show_spinner=False)
def load_events() -> dict:
    if os.path.exists(config.EVENTS_JSON):
        with open(config.EVENTS_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


@st.cache_data(ttl=120, show_spinner=False)
def load_alert_center() -> list:
    if os.path.exists(config.ALERTS_CENTER_JSON):
        with open(config.ALERTS_CENTER_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return []


@st.cache_data(ttl=120, show_spinner=False)
def load_universe() -> dict:
    if os.path.exists(config.UNIVERSE_JSON):
        with open(config.UNIVERSE_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


@st.cache_data(ttl=120, show_spinner=False)
def load_system_health() -> dict:
    if os.path.exists(config.SYSTEM_HEALTH_JSON):
        with open(config.SYSTEM_HEALTH_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


@st.cache_data(ttl=1800, show_spinner=False)
def deepdive_fetch(ticker: str):
    """Live per-ticker data pull for the Company Deep Dive (cached 30 min)."""
    import deepdive
    return deepdive.fetch_bundle(ticker)


@st.cache_data(ttl=120, show_spinner=False)
def load_backtest() -> dict:
    if os.path.exists(config.BACKTEST_JSON):
        with open(config.BACKTEST_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


@st.cache_data(ttl=120, show_spinner=False)
def load_portfolio() -> dict:
    if os.path.exists(config.PORTFOLIO_JSON):
        with open(config.PORTFOLIO_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {"empty": True}


@st.cache_data(ttl=300, show_spinner=False)
def read_outputs():
    d = config.OUTPUTS_DIR
    a = os.path.join(d, "alerts.csv")
    b = os.path.join(d, "backtest_summary.xlsx")
    alerts = pd.read_csv(a) if os.path.exists(a) else pd.DataFrame()
    backtest = pd.read_excel(b) if os.path.exists(b) else pd.DataFrame()
    return alerts, backtest


@st.cache_data(ttl=1800, show_spinner=False)
def get_news_sentiment(symbol: str):
    heads = get_headlines(symbol, config.NEWS_LIMIT)
    return heads, score_headlines(heads)


def run_scan():
    """Run the full pipeline (used for first-load and the refresh button)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([sys.executable, "run.py"], cwd=root, timeout=300,
                   env=dict(os.environ, STOCK_AGENT_DISABLE_EMAIL="1", PYTHONUTF8="1"),
                   capture_output=True, text=True)


# First load / cloud: generate data if missing (self-sufficient).
if not os.path.exists(config.RESULTS_CSV):
    st.info("טוען נתונים בפעם הראשונה — מבצע סריקה ראשונית (כ‑30–60 שניות)…")
    with st.spinner("סורק את רשימת המעקב…"):
        try:
            run_scan()
        except Exception:
            pass
    if not os.path.exists(config.RESULTS_CSV):
        st.error("הסריקה הראשונית נכשלה. נסו לרענן את הדף.")
        st.stop()
    st.cache_data.clear()

df = load_results()
mkt = load_market()
closes = load_closes()
events = load_events()


def _is_mobile() -> bool:
    """True on a narrow screen (?m=1) — auto-detected via a tiny JS probe.

    On a phone (innerWidth < 500) the probe reloads once with ?m=1; on desktop
    it does nothing. ?m=0 forces desktop. Desktop code path is unchanged.
    """
    qp = st.query_params
    if "m" in qp:
        return str(qp.get("m")) == "1"
    components.html(
        """<script>
          const u = new URL(window.parent.location.href);
          if (!u.searchParams.has('m') && window.parent.innerWidth < 500) {
            u.searchParams.set('m', '1');
            window.parent.location.replace(u.toString());
          }
        </script>""", height=0)
    return False


# Phase 16: branch to the dedicated mobile experience on narrow screens.
if _is_mobile():
    from dashboard import mobile as mobile_ui
    mobile_ui.render(df, mkt)
    st.stop()

positive = df[df["_group"] == "positive"]
watch = df[df["_group"] == "watch"]
avoid = df[df["_group"] == "avoid"]
n_break = int(df["Breakout"].sum())
latest = mkt.get("date", df["Date"].iloc[0] if len(df) else "—")


# ===========================================================================
# Top bar + sidebar
# ===========================================================================

st.markdown(
    f"""<div class="topbar">
      <div style="font-size:20px;font-weight:800">🤖 Stock Agent <span style="color:{BLUE}">Pro</span>
        <span style="color:{MUTED};font-size:13px">v3.0</span></div>
      <div><span class="pill">● המערכת מעודכנת</span>
        <span style="color:{MUTED};margin-right:14px">{latest}</span></div>
    </div>""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "תצוגה",
    ["🏠 ראשי (60 שניות)", "🔭 סורק שוק", "🔎 ניתוח חברה", "🤖 עוזר", "📈 מניות ופירוט", "🗺️ סקטורים",
     "💼 תיק", "🧭 החלטות תיק", "🛡️ אמון ואימות", "🔔 התראות", "📰 חדשות", "📊 בקטסט"],
)
st.sidebar.caption(f"{len(df)} מניות · עודכן {latest}")
st.sidebar.divider()
if st.sidebar.button("📱 תצוגת מובייל", use_container_width=True):
    st.query_params["m"] = "1"
    st.rerun()
if st.sidebar.button("🔄 רענן נתונים עכשיו", use_container_width=True,
                     help="מריץ סריקה מחדש (כ‑30–60 שניות). ללא שליחת מייל."):
    with st.spinner("מריץ סריקה מחדש…"):
        try:
            run_scan(); ok = True
        except Exception:
            ok = False
    if ok:
        st.cache_data.clear(); st.sidebar.success("עודכן!"); st.rerun()
    else:
        st.sidebar.error("הרענון נכשל.")


def chart_series(ticker):
    """Recent closes for a ticker from the precomputed artifact (instant)."""
    return closes.get(ticker, [])


# ===========================================================================
# Reusable renderers
# ===========================================================================

def fear_greed_gauge(fng: dict):
    score = fng.get("score")
    if score is None:
        st.caption("מד פחד/חמדנות: אין נתון.")
        return
    color = RED if score < 45 else (GREEN if score > 55 else AMBER)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"color": TEXT, "size": 30}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED},
            "bar": {"color": color},
            "steps": [{"range": [0, 45], "color": "#3b1f24"},
                      {"range": [45, 55], "color": "#3a341f"},
                      {"range": [55, 100], "color": "#10331f"}],
        },
    ))
    style_fig(fig, 200)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(f"<div style='text-align:center;color:{color};font-weight:700'>"
                f"{fng.get('label','')}</div>", unsafe_allow_html=True)


def opportunity_card(rank, r):
    info = classify(r)
    up = fmt(r.get("ExpectedUpside%"), "%")
    conf = fmt(r.get("Confidence"), "")
    chg = r.get("DailyChange%", 0)
    ccol = GREEN if chg >= 0 else RED
    ex = explain_stock(r, events.get(r["Ticker"]))
    why_key = {"positive": ("✅ למה כן", ex["why_buy"]),
               "watch": ("🟡 למה במעקב", ex["why_watch"] or ex["why_buy"]),
               "avoid": ("🔴 למה להימנע", ex["why_avoid"])}[ex["group"]]
    why_items = "".join(f"<li>{x}</li>" for x in why_key[1][:3])
    cats = "".join(f"<li>{x}</li>" for x in ex["catalysts"][:2])
    rsks = "".join(f"<li>{x}</li>" for x in ex["risks"][:2])
    st.markdown(
        f"""<div class="card" style="border-right:5px solid {info['color']}">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div style="font-size:17px;font-weight:800">#{rank} &nbsp; {r['Ticker']}
              <span style="color:{MUTED};font-weight:400">· {r['Name']}</span></div>
            <div style="color:{info['color']};font-weight:700">{info['emoji']} {info['label']}</div>
          </div>
          <div style="margin:8px 0;color:{TEXT}">
            ציון סופי <b>{int(r['ScoreV2'])}</b>/100 <span style="color:{MUTED};font-size:12px">(טכני {int(r['Score'])})</span> ·
            מחיר ${fmt(r['Price'])} <span style="color:{ccol}">({'+' if chg>=0 else ''}{chg}%)</span> ·
            פוטנציאל עלייה <b style="color:{GREEN}">{up}</b> ·
            ביטחון <b>{conf}</b> ({fmt(r.get('ConfidenceLevel'))}) ·
            סיכון {fmt(r.get('RiskLevel'))}
          </div>
          <div style="display:flex;gap:24px;flex-wrap:wrap;font-size:13px">
            <div><b style="color:{info['color']}">{why_key[0]}</b>
              <ul style="margin:4px 0;color:{MUTED};padding-right:18px">{why_items}</ul></div>
            <div><b style="color:{GREEN}">⚡ קטליזטורים</b>
              <ul style="margin:4px 0;color:{MUTED};padding-right:18px">{cats}</ul></div>
            <div><b style="color:{RED}">⚠️ סיכונים</b>
              <ul style="margin:4px 0;color:{MUTED};padding-right:18px">{rsks}</ul></div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE: 60-second home (Market Overview + Top Opportunities)
# ===========================================================================

def kpi_html(ac, ico, val, lab, sub, tip=""):
    """One institutional KPI card (icon, big number, label, sub, color, tooltip)."""
    return (f"<div class='kpi' style='--ac:{ac}' title='{tip}'><span class='k-dot'></span>"
            f"<div class='k-ico'>{ico}</div><div class='k-val'>{val}</div>"
            f"<div class='k-lab'>{lab}</div><div class='k-sub'>{sub}</div></div>")


def _sector_raw(r):
    """Raw 0-100 sector score for a stock (EN sector → HE → market score)."""
    secs = {s.get("sector"): s.get("score") for s in mkt.get("sectors", [])}
    return secs.get(market.SECTOR_EN_TO_HE.get(r.get("Sector")))


def regime_gauge(score, label):
    """Premium angular gauge for the market regime."""
    if not isinstance(score, (int, float)):
        st.caption("מצב שוק: אין נתון.")
        return
    col = regime_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"color": col, "size": 46}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED, "tickwidth": 1},
            "bar": {"color": col, "thickness": 0.30},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [{"range": [0, 40], "color": "#2a1320"},
                      {"range": [40, 60], "color": "#2c2a12"},
                      {"range": [60, 100], "color": "#0f2e1c"}],
            "threshold": {"line": {"color": col, "width": 4}, "thickness": 0.85, "value": score},
        },
    ))
    style_fig(fig, 200)
    fig.update_layout(margin=dict(l=20, r=20, t=8, b=0))
    st.plotly_chart(fig, use_container_width=True)


def action_card_html(idx, h):
    """HTML for one 'what should I do today' action card from a decision dict."""
    pr = {1: "עדיפות 1", 2: "עדיפות 2", 3: "עדיפות 3"}.get(idx, "")
    verb = {"Increase": "הגדל", "Reduce": "הקטן", "Exit": "צא מ-", "Hold": "החזק"}.get(h["action"], h["action"])
    ac = NEGATIVE if h.get("priority") == "גבוהה" else (WARNING if h.get("priority") == "בינונית" else PRIMARY)
    benefit = {"Reduce": "מקרב לפיזור היעד ומפחית ריכוז",
               "Exit": "מסיר חשיפה לא-אטרקטיבית",
               "Increase": "מגדיל חשיפה לאיכות"}.get(h["action"], "מיישר את התיק ליעד")
    return (f"<div class='act' style='--ac:{ac}'>"
            f"<div class='a-pr'>🎯 {pr} · {h.get('priority','')}</div>"
            f"<div class='a-ti'>{verb} {h['ticker']} → {h['target_pct']}% "
            f"<span style='color:{MUTED};font-weight:500'>(כעת {h['current_pct']}%)</span></div>"
            f"<div class='a-row'><b>למה:</b> {h.get('reasoning','')}</div>"
            f"<div class='a-row'><b>השפעת סיכון:</b> {h.get('risk_impact','')}</div>"
            f"<div class='a-row'><b>תועלת צפויה:</b> {benefit}</div>"
            f"<div class='a-row'><b>ביטחון:</b> {h.get('confidence','—')}%</div></div>")


def opp_card(rank, r):
    """Institutional opportunity card: sparkline + score bars + meta + reasons."""
    info = classify(r)
    tk = r["Ticker"]
    chg = r.get("DailyChange%", 0) or 0
    ccol = POSITIVE if chg >= 0 else NEGATIVE
    spark = sparkline_svg(chart_series(tk))
    trust = r.get("TrustScore")
    risk = r.get("ScoreRisk")
    risk_health = None if (risk is None or risk != risk) else 100 - risk
    bars = (score_bar("טכני", r.get("Score")) + score_bar("פונדמנטלי", r.get("ScoreFundamental"))
            + score_bar("סקטור", _sector_raw(r)) + score_bar("חדשות", r.get("ScoreNews"))
            + score_bar("ניהול סיכון", risk_health) + score_bar("אמון", trust))
    ex = explain_stock(r, events.get(tk))
    why = {"positive": ex["why_buy"], "watch": ex["why_watch"] or ex["why_buy"],
           "avoid": ex["why_avoid"]}[ex["group"]]
    whys = "".join(f"<li>{x}</li>" for x in (why or [])[:2]) or "<li>—</li>"
    rsks = "".join(f"<li>{x}</li>" for x in ex["risks"][:2]) or "<li>—</li>"
    cats = "".join(f"<li>{x}</li>" for x in ex["catalysts"][:2]) or "<li>—</li>"
    trust_disp = fmt(int(trust) if isinstance(trust, (int, float)) and trust == trust else None)
    st.markdown(
        f"""<div class="opp" style="--ac:{info['color']}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div><span class="o-tick">#{rank} {tk}</span> <span class="o-co">{r['Name']}</span></div>
            <div style="text-align:left">{spark}
              <div class="o-rec" style="color:{info['color']}">{info['emoji']} {info['label']}</div></div>
          </div>
          <div class="o-meta">
            <span>ציון V2 <b>{int(r['ScoreV2'])}</b></span>
            <span>אמון <b>{trust_disp}</b></span>
            <span>סיכון <b>{fmt(r.get('RiskLevel'))}</b></span>
            <span>פוטנציאל <b style="color:{POSITIVE}">{fmt(r.get('ExpectedUpside%'),'%')}</b></span>
            <span>${fmt(r.get('Price'))} <span style="color:{ccol}">({'+' if chg>=0 else ''}{chg}%)</span></span>
            <span>{fmt(r.get('Sector'))}</span>
          </div>
          <div class="o-cols">
            <div>{bars}</div>
            <div><b style="color:{info['color']}">למה מעניין</b><ul>{whys}</ul>
                 <b style="color:{NEGATIVE}">סיכונים עיקריים</b><ul>{rsks}</ul></div>
            <div><b style="color:{PRIMARY}">אירועים / קטליזטורים</b><ul>{cats}</ul></div>
          </div>
        </div>""", unsafe_allow_html=True)


if page.startswith("🏠"):
    regime = mkt.get("regime", {})
    fng = mkt.get("fear_greed", {})
    breadth = mkt.get("breadth", {})
    indices = mkt.get("indices", [])
    ins = mkt.get("insights", {})
    pf = load_portfolio()
    alerts = load_alert_center()
    health = load_system_health()

    # ---------- Section 1: Executive KPI strip ----------
    reg_s, reg_l = regime.get("score"), regime.get("label", "—")
    fg_s, fg_l = fng.get("score"), fng.get("label", "")
    fg_c = (NEGATIVE if isinstance(fg_s, (int, float)) and fg_s < 45
            else POSITIVE if isinstance(fg_s, (int, float)) and fg_s > 55 else WARNING)
    crit = [a for a in alerts if a.get("severity") in ("קריטית", "גבוהה")]
    hp = (pf.get("health") or {}).get("score") if not pf.get("empty") else None
    tr = health.get("avg_trust")

    def _kpi(ac, ico, val, lab, sub, tip):
        return (f"<div class='kpi' style='--ac:{ac}' title='{tip}'><span class='k-dot'></span>"
                f"<div class='k-ico'>{ico}</div><div class='k-val'>{val}</div>"
                f"<div class='k-lab'>{lab}</div><div class='k-sub'>{sub}</div></div>")

    kpis = [
        _kpi(regime_color(reg_s), "🧭", fmt(reg_s), "מצב שוק", reg_l,
             "ציון 0-100 ממגמת S&P 500, רמת VIX ורוחב שוק"),
        _kpi(fg_c, "😶‍🌫️", fmt(fg_s), "פחד / חמדנות", fg_l,
             "מדד קנייני: VIX + רוחב + מומנטום + יחס עולות/יורדות"),
        _kpi(POSITIVE, "💎", len(positive), "הזדמנויות", f"{n_break} פריצות · {len(watch)} מעקב",
             "מספר המניות בסטטוס חיובי היום"),
        _kpi(NEGATIVE if crit else MUTED, "🔔", len(crit), "התראות קריטיות", f"מתוך {len(alerts)} סה\"כ",
             "התראות בחומרה גבוהה/קריטית"),
        _kpi(score_color(hp), "💼", fmt(hp), "בריאות תיק", "פיזור · ריכוז · סיכון" if hp is not None else "אין תיק",
             "ציון בריאות התיק 0-100"),
        _kpi(score_color(tr), "🛡️", fmt(round(tr) if isinstance(tr, (int, float)) else None), "ציון אמון",
             "ממוצע מערכת", "ממוצע ציון האמון על פני המניות שנסרקו"),
    ]
    st.markdown(f"<div class='kpi-grid'>{''.join(kpis)}</div>", unsafe_allow_html=True)

    # ---------- Section 2: Market Regime + What should I do today ----------
    c = st.columns([1.05, 1.95], gap="large")
    with c[0]:
        st.markdown("#### 🧭 מצב שוק (Market Regime)")
        regime_gauge(reg_s, reg_l)
        spx = mkt.get("spx_hist", [])
        spx_up = len(spx) > 20 and spx[-1] >= sum(spx) / len(spx)
        vix = next((i.get("price") for i in indices if i.get("symbol") == "^VIX"), None)
        vix_low = isinstance(vix, (int, float)) and vix < 20
        br = breadth.get("above200")
        br_pos = isinstance(br, (int, float)) and br >= 50

        def _chip(ok, label):
            cc = POSITIVE if ok else NEGATIVE
            return f"<span class='badge' style='color:{cc};background:{cc}1a;margin:3px 3px 0 0'>{'✓' if ok else '✕'} {label}</span>"
        st.markdown("<div>" + _chip(spx_up, "S&P 500 מעל המגמה")
                    + _chip(vix_low, f"VIX נמוך ({fmt(vix)})")
                    + _chip(br_pos, f"רוחב חיובי ({fmt(br, '%')})")
                    + f"<div class='ic-sub' style='margin-top:8px'>גורמים תורמים — נגזרים מ-S&P מול ממוצעים 200/50 ורמת VIX.</div></div>",
                    unsafe_allow_html=True)
    with c[1]:
        st.markdown("#### ✅ מה לעשות היום?")
        decisions = pf.get("decisions") or {}
        holds = [h for h in decisions.get("holdings", []) if h.get("action") != "Hold"]
        holds.sort(key=lambda h: {"גבוהה": 0, "בינונית": 1, "נמוכה": 2}.get(h.get("priority"), 3))
        if holds:
            grid = "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px'>"
            grid += "".join(action_card_html(i, h) for i, h in enumerate(holds[:3], start=1))
            st.markdown(grid + "</div>", unsafe_allow_html=True)
            extras = decisions.get("rebalancing_actions", []) or decisions.get("today", [])
            extras = [e for e in extras if not e.startswith(("🟡", "🟢", "🔴"))][:3]
            if extras:
                st.markdown("<div class='ic-sub' style='margin-top:10px'>" +
                            "".join(f"• {e}<br>" for e in extras) + "</div>", unsafe_allow_html=True)
        else:
            top3 = (positive if not positive.empty else df).sort_values("ScoreV2", ascending=False).head(3)
            grid = "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px'>"
            for i, (_, r) in enumerate(top3.iterrows(), start=1):
                info = classify(r)
                grid += (f"<div class='act' style='--ac:{PRIMARY}'><div class='a-pr'>🎯 עדיפות {i}</div>"
                         f"<div class='a-ti'>בחן {r['Ticker']}</div>"
                         f"<div class='a-row'><b>למה:</b> {info['summary']}</div>"
                         f"<div class='a-row'><b>ציון V2:</b> {int(r['ScoreV2'])} · <b>ביטחון:</b> {fmt(r.get('Confidence'))}%</div></div>")
            st.markdown(grid + "</div>", unsafe_allow_html=True)
            st.caption("אין תיק פעיל — להפעלת פעולות תיק, מלא portfolio.csv.")

    # ---------- Section 3: Markets strip + S&P trend ----------
    st.markdown("#### 🌐 שווקים")
    cells = []
    for ix in indices:
        cp = ix.get("change_pct")
        col = MUTED if cp is None else (POSITIVE if cp >= 0 else NEGATIVE)
        sign = "+" if (cp is not None and cp >= 0) else ""
        cells.append(f"<span style='margin-left:24px'><b style='color:{TEXT}'>{ix['name']}</b> "
                     f"{fmt(ix.get('price'))} <span style='color:{col}'>{sign}{fmt(cp)}%</span></span>")
    st.markdown(f"<div class='ic-card' style='padding:14px 20px'>{''.join(cells)}</div>", unsafe_allow_html=True)
    spx = mkt.get("spx_hist", [])
    if spx:
        fig = go.Figure(go.Scatter(y=spx, line_color=PRIMARY, fill="tozeroy", fillcolor="rgba(0,194,255,0.10)"))
        fig.update_layout(title="S&P 500 · מגמת 6 חודשים")
        st.plotly_chart(style_fig(fig, 210), use_container_width=True)
    with st.expander("ℹ️ איך מחושבים מצב השוק ומד הפחד/חמדנות?"):
        st.write(fng.get("method", "—"))
        st.write("**רוחב שוק:** " + breadth.get("method", "—"))

    st.divider()

    # ---------- Section 4: Top opportunities (cards + drill-down) ----------
    st.markdown("### 💎 ההזדמנויות המובילות היום")
    ranked = positive.sort_values("ScoreV2", ascending=False) if not positive.empty \
        else df.sort_values("ScoreV2", ascending=False)
    if ranked.empty:
        st.caption("אין הזדמנויות חיוביות היום.")
    else:
        analyzed = st.session_state.setdefault("analyzed", set())
        t3, t5, t10 = st.tabs(["Top 3", "Top 5", "Top 10"])
        for tab, k in [(t3, 3), (t5, 5), (t10, 10)]:
            with tab:
                shown = ranked.head(k)
                if shown.empty:
                    st.caption("אין מספיק מניות.")
                for rank, (_, r) in enumerate(shown.iterrows(), start=1):
                    tk = r["Ticker"]
                    opp_card(rank, r)
                    b = st.columns([1, 1, 6])
                    if b[0].button("🔍 ניתוח", key=f"an_{k}_{tk}"):
                        analyzed.discard(tk) if tk in analyzed else analyzed.add(tk)
                        st.rerun()
                    if b[1].button("➕ לתיק", key=f"add_{k}_{tk}"):
                        st.toast(f"להוספת {tk} לתיק: ערוך portfolio.csv (Ticker,Quantity,AverageCost) ולחץ רענון.", icon="➕")
                    if tk in analyzed:
                        ex = explain_stock(r, events.get(tk))
                        full_why = "".join(f"<li>{x}</li>" for x in (ex["why_buy"] or ex["why_watch"] or [])[:5]) or "<li>—</li>"
                        full_rsk = "".join(f"<li>{x}</li>" for x in ex["risks"][:5]) or "<li>—</li>"
                        full_cat = "".join(f"<li>{x}</li>" for x in ex["catalysts"][:5]) or "<li>—</li>"
                        st.markdown(
                            f"""<div class='ic-card' style='--ac:{classify(r)['color']}'>
                              <div class='ic-title'>🔍 ניתוח מעמיק · {tk}</div>
                              <div class='o-cols' style='margin-top:6px'>
                                <div><b style='color:{POSITIVE}'>מדוע</b><ul style='padding-right:16px;color:{MUTED}'>{full_why}</ul></div>
                                <div><b style='color:{NEGATIVE}'>סיכונים</b><ul style='padding-right:16px;color:{MUTED}'>{full_rsk}</ul></div>
                                <div><b style='color:{PRIMARY}'>קטליזטורים / אירועים</b><ul style='padding-right:16px;color:{MUTED}'>{full_cat}</ul></div>
                              </div></div>""", unsafe_allow_html=True)
        st.caption("פוטנציאל עלייה וביטחון = מדדים קנייניים מחושבים (ראו עמוד 'מניות ופירוט' להסבר).")


# ===========================================================================
# PAGE: AI assistant
# ===========================================================================

elif page == "🔭 סורק שוק":
    st.markdown("### 🔭 סורק שוק — מנוע גילוי הזדמנויות מרחבי השוק")
    uni = load_universe()
    if not uni:
        st.info("הסריקה הרחבה עדיין לא רצה. הרץ במסוף: `python scanner.py ALL` (כ‑1.5 דקות), ואז רענן.")
    else:
        c = st.columns(4)
        c[0].metric("מניות נסרקו", uni.get("scanned"))
        c[1].metric("הועשרו (Top)", uni.get("enriched"))
        c[2].metric("יקום", uni.get("universe"))
        c[3].metric("זמן סריקה", f"{uni.get('elapsed_sec')}s")
        st.caption("שלב א׳ (כל היקום): טכני/סיכון/מומנטום מהמחירים. שלב ב׳ (Top): פונדמנטל/composite/בקטסט.")

        rk = uni.get("rankings", {})
        rnames = [("opportunities", "🏆 הזדמנויות"), ("undervalued", "💰 מוערכות בחסר"),
                  ("momentum", "🚀 מומנטום"), ("high_quality", "⭐ איכות גבוהה"),
                  ("turnarounds", "🔄 תפניות")]
        st.markdown("#### דירוגי Top 10")
        rcols = st.columns(5)
        for i, (k, label) in enumerate(rnames):
            with rcols[i]:
                st.markdown(f"**{label}**")
                for t in (rk.get(k) or [])[:10]:
                    st.markdown(f"<div style='font-size:13px'>{t}</div>", unsafe_allow_html=True)
                if not rk.get(k):
                    st.caption("—")

        sd = uni.get("sector_distribution", {})
        if sd:
            fig = go.Figure(go.Bar(x=list(sd.values()), y=list(sd.keys()), orientation="h",
                                   marker_color=BLUE))
            fig.update_layout(title="התפלגות סקטורים (הזדמנויות)")
            st.plotly_chart(style_fig(fig, 300), use_container_width=True)

        opps = pd.DataFrame(uni.get("opportunities", []))
        st.markdown("#### 🔎 סינון הזדמנויות")
        if opps.empty:
            st.caption("אין הזדמנויות מועשרות.")
        else:
            f = st.columns(4)
            secs = sorted([s for s in opps.get("Sector", pd.Series()).dropna().unique()])
            sel_sec = f[0].multiselect("סקטור", secs)
            min_score = f[1].slider("ScoreV2 מינ׳", 0, 100, 0)
            risk_opt = f[2].selectbox("סיכון מקס׳", ["הכל", "נמוך", "בינוני", "גבוה", "גבוה מאוד"])
            cap_opt = f[3].selectbox("שווי שוק", ["הכל", "Large (>$10B)", "Mid/Small (<$10B)"])
            g = st.columns(3)
            min_val = g[0].slider("שווי (Valuation) מינ׳", 0, 100, 0)
            min_mom = g[1].slider("מומנטום 3ח׳ מינ׳ %", -50, 100, -50)
            min_qual = g[2].slider("איכות (פונדמנטלי) מינ׳", 0, 100, 0)

            order = {"נמוך": 0, "בינוני": 1, "גבוה": 2, "גבוה מאוד": 3}
            v = opps.copy()
            if sel_sec:
                v = v[v["Sector"].isin(sel_sec)]
            v = v[v["ScoreV2"].fillna(0) >= min_score]
            if risk_opt != "הכל":
                v = v[v["RiskLevel"].map(lambda x: order.get(x, 9)) <= order[risk_opt]]
            if "Valuation" in v:
                v = v[v["Valuation"].fillna(0) >= min_val]
            if "Ret3m" in v:
                v = v[v["Ret3m"].fillna(-999) >= min_mom]
            if "ScoreFundamental" in v:
                v = v[v["ScoreFundamental"].fillna(0) >= min_qual]
            if cap_opt != "הכל" and "MarketCap" in v:
                mc = v["MarketCap"].fillna(0)
                v = v[mc >= 10e9] if cap_opt.startswith("Large") else v[mc < 10e9]

            sec_rank = {s["sector"]: i for i, s in enumerate(
                sorted(mkt.get("sectors", []), key=lambda x: -x.get("score", 0)), 1)}

            def srank(en):
                return sec_rank.get(market.SECTOR_EN_TO_HE.get(en))

            show = [{"סימול": r["Ticker"], "שם": r.get("Name"), "סקטור": r.get("Sector"),
                     "דירוג סקטור": srank(r.get("Sector")), "ScoreV2": r.get("ScoreV2"),
                     "סיכון": r.get("RiskScore"), "שווי": r.get("Valuation"),
                     "מומנטום 3ח׳ %": r.get("Ret3m"), "הצלחה היסט׳": r.get("HistWinRate"),
                     "ביטחון": r.get("Confidence"),
                     "תגיות": " · ".join(r["tags"]) if isinstance(r.get("tags"), list) else ""}
                    for _, r in v.iterrows()]
            st.markdown(f"**{len(show)} הזדמנויות** (מתוך {uni.get('enriched')} מועשרות)")
            st.dataframe(pd.DataFrame(show), use_container_width=True, hide_index=True, column_config={
                "ScoreV2": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
                "שווי": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
                "הצלחה היסט׳": st.column_config.NumberColumn(format="%.0f%%")})
        st.caption("הסינון על ההזדמנויות המועשרות (Top שעברו פונדמנטל). דירוג מומנטום מכסה את כל היקום.")

elif page == "🤖 עוזר":
    st.markdown("#### 🤖 עוזר חכם — שאל שאלה על המניות שלך")
    st.caption("דוגמאות: \"מה המניות הכי חזקות?\" · \"מה הציון של NVDA?\" · "
               "\"כמה מועמדות לפריצה?\" · \"מה מצב השוק?\"")
    if "chat" not in st.session_state:
        st.session_state.chat = [("assistant",
            "שלום! 👋 שאל אותי בעברית על תוצאות הסריקה.")]
    for role, msg in st.session_state.chat:
        with st.chat_message(role, avatar=("🤖" if role == "assistant" else "🙂")):
            st.markdown(msg, unsafe_allow_html=True)
    q = st.chat_input("הקלד שאלה בעברית…")
    if q:
        st.session_state.chat.append(("user", q))
        with st.chat_message("user", avatar="🙂"):
            st.markdown(q)
        ans = assistant_answer(q, df, mkt)
        st.session_state.chat.append(("assistant", ans))
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(ans, unsafe_allow_html=True)


# ===========================================================================
# PAGE: stocks + detail
# ===========================================================================

elif page == "📈 מניות ופירוט":
    st.markdown("#### 📋 כל המניות — שקיפות ציונים")
    sectors_data = mkt.get("sectors", [])
    rows = []
    for rank, (_, r) in enumerate(df.iterrows(), start=1):
        info = classify(r)
        rows.append({
            "דירוג": rank, "סימול": r["Ticker"], "שם": r["Name"],
            "מחיר": r["Price"], "שינוי %": r["DailyChange%"],
            "סופי v2": int(r["ScoreV2"]),
            "טכני": int(r["Score"]),
            "פונדמנטלי": r.get("ScoreFundamental"),
            "סקטור": market.sector_score_for(r.get("Sector"), sectors_data),
            "סיכון": r.get("ScoreRisk"),
            "המלצה": f"{info['emoji']} {info['label']}",
            "מגמה": chart_series(r["Ticker"]),
        })
    bar = lambda: st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")
    st.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True,
        column_config={
            "מחיר": st.column_config.NumberColumn(format="$%.2f"),
            "שינוי %": st.column_config.NumberColumn(format="%.2f%%"),
            "סופי v2": bar(), "טכני": bar(), "פונדמנטלי": bar(),
            "סקטור": bar(), "סיכון": bar(),
            "מגמה": st.column_config.LineChartColumn(width="small"),
        },
    )
    st.caption("ציון סופי = הציון הטכני-מומנטום שמדרג. פונדמנטלי/סקטור/סיכון = עדשות "
               "משלימות (0–100). ציון חדשות מוצג בכרטיס המניה (נמשך בזמן אמת).")
    st.divider()
    st.markdown("#### 🔍 כרטיס מניה")
    sym = st.selectbox("בחר מניה", df["Ticker"].tolist())
    r = df[df["Ticker"] == sym].iloc[0]
    info = classify(r)
    heads, news_sent = get_news_sentiment(sym)
    series = chart_series(sym)
    fs = factor_scores(r, closes=series, fundamentals=r, news_sent=news_sent)

    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"### {info['emoji']} {sym} — {r['Name']}")
        st.markdown(f"<div style='color:{info['color']};font-weight:bold;font-size:17px'>{info['summary']}</div>"
                    f"<div style='color:{MUTED};margin-bottom:8px'>{info['detail']}</div>",
                    unsafe_allow_html=True)
        if series:
            fig = go.Figure(go.Scatter(y=series, line_color=BLUE, fill="tozeroy"))
            st.plotly_chart(style_fig(fig, 260), use_container_width=True)
        action = {"positive": "✅ קנייה / מעקב חיובי", "watch": "🟡 מעקב",
                  "avoid": "🔴 להימנעות"}[info["group"]]
        st.markdown(f"<div class='card'><b>פעולה מוצעת:</b> {action} · "
                    f"פוטנציאל עלייה {fmt(r.get('ExpectedUpside%'),'%')} · "
                    f"ביטחון {fmt(r.get('Confidence'))} ({fmt(r.get('ConfidenceLevel'))})</div>",
                    unsafe_allow_html=True)
        # Structured explanation (Phase 5)
        ex = explain_stock(r, events.get(sym))
        e1, e2 = st.columns(2)
        with e1:
            st.markdown("**✅ למה כן (Why Buy)**")
            for x in ex["why_buy"]:
                st.markdown(f"- {x}")
            if ex["why_watch"]:
                st.markdown("**🟡 למה במעקב**")
                for x in ex["why_watch"]:
                    st.markdown(f"- {x}")
        with e2:
            st.markdown("**🔴 למה לא (Why Avoid)**")
            for x in (ex["why_avoid"] or ["אין סיבות הימנעות בולטות."]):
                st.markdown(f"- {x}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**⚡ קטליזטורים (Key Catalysts)**")
            for x in ex["catalysts"]:
                st.markdown(f"- {x}")
        with c2:
            st.markdown("**⚠️ סיכונים (Key Risks)**")
            for x in ex["risks"]:
                st.markdown(f"- {x}")
    sec_score = market.sector_score_for(r.get("Sector"), mkt.get("sectors", []))
    with right:
        axes = ["טכני", "פונדמנטלי", "סקטור", "חדשות", "ביטחון"]
        vals = [fs["technical"], fs["fundamental"] or 0, sec_score or 0,
                fs["news"] or 50, 100 - fs["risk"]]
        fig = go.Figure(go.Scatterpolar(r=vals + [vals[0]], theta=axes + [axes[0]],
                                        fill="toself", line_color=GREEN))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])))
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)

    st.markdown("##### 🎯 פירוט הציונים")
    m = st.columns(6)
    v2 = int(r["ScoreV2"]); v1 = int(r["Score"]); delta = v2 - v1
    m[0].metric("⭐ סופי v2", v2, f"{delta:+d} מול טכני")
    m[1].metric("טכני (v1)", fmt(fs["technical"]))
    m[2].metric("פונדמנטלי", fmt(fs["fundamental"], dash="אין נתון"))
    m[3].metric("סקטור", fmt(sec_score, dash="אין נתון"))
    m[4].metric("חדשות", fmt(fs["news"]))
    m[5].metric("סיכון", fmt(fs["risk"]))

    # Composite v2 contribution breakdown (sums to the v2 score).
    st.markdown("**🧮 מרכיבי הציון הסופי v2** (פונדמנטלי 35% · טכני 25% · סקטור 20% · חדשות 10% · סיכון 10%)")
    contrib = {"פונדמנטלי": r.get("ContribFund"), "טכני": r.get("ContribTech"),
               "סקטור": r.get("ContribSector"), "חדשות": r.get("ContribNews"),
               "ניהול סיכון": r.get("ContribRisk")}
    bars = "".join(
        f"<div style='margin:3px 0'>{name}: <b>{fmt(v,' נק׳')}</b>"
        f"<div style='background:#233456;border-radius:4px;height:8px;width:100%'>"
        f"<div style='background:{GREEN};height:8px;border-radius:4px;"
        f"width:{min(100,(v or 0)/35*100):.0f}%'></div></div></div>"
        for name, v in contrib.items())
    st.markdown(f"<div class='card'>{bars}"
                f"<div style='margin-top:8px;color:{MUTED};font-size:13px'>"
                f"סכום = <b>{v2}</b> = הציון הסופי · שלמות נתונים {fmt(r.get('Completeness'),'%')}</div></div>",
                unsafe_allow_html=True)
    with st.expander("🔎 פירוק הציון הטכני (רכיב מתוך v2)"):
        bd = score_breakdown(r)
        for k, val in bd.items():
            st.markdown(f"- **{COMPONENT_LABELS_HE.get(k, k)}:** {val} נק׳")
        st.caption(f"סכום הרכיבים הטכניים = {int(round(sum(bd.values())))} = הציון הטכני (25% מ-v2).")

    # Risk Intelligence panel (Part 2): beta / volatility / max drawdown.
    st.markdown("##### 🛡️ פרופיל סיכון")
    rk = st.columns(4)
    rk[0].metric("ביתא", fmt(r.get("Beta"), dash="אין נתון"))
    rk[1].metric("תנודתיות שנתית", fmt(r.get("Volatility"), "%", dash="אין נתון"))
    rk[2].metric("ירידה מקסימלית", fmt(r.get("MaxDrawdown"), "%", dash="אין נתון"))
    rk[3].metric("רמת סיכון", fmt(r.get("RiskLevel")))
    rw = r.get("RiskWarnings")
    if isinstance(rw, str) and rw.strip():
        st.markdown("<div class='card' style='border-right:4px solid " + RED + "'>⚠️ " +
                    rw.replace(" · ", "<br>⚠️ ") + "</div>", unsafe_allow_html=True)
    st.caption("ביתא = רגישות לשוק (S&P 500) · תנודתיות שנתית · ירידה מקסימלית = הנפילה "
               "הגדולה ביותר מהשיא בשנה האחרונה. ציון הסיכון מזין את הציון הסופי v2.")

    # "Why should I trust this recommendation?" (Part 4 — backtest validation)
    bt = load_backtest().get(sym)
    st.markdown("##### 🤔 למה לסמוך על ההמלצה?")
    if bt and bt.get("occurrences"):
        cset = {"גבוה": GREEN, "בינוני": AMBER, "נמוך": RED}.get(bt.get("confidence"), MUTED)
        b = st.columns(4)
        b[0].metric("מופעים דומים בעבר", bt["occurrences"])
        b[1].metric("אחוז הצלחה", fmt(bt.get("win_rate"), "%"))
        b[2].metric("תשואה ממוצעת", fmt(bt.get("avg_return"), "%"))
        b[3].metric("OOS הצלחה", fmt(bt.get("oos_win_rate"), "%", dash="—"))
        st.markdown(
            f"<div class='card'>רמת ביטחון: <b style='color:{cset}'>{bt.get('confidence')}</b> · "
            f"תשואה חציונית {fmt(bt.get('median_return'), '%')} · "
            f"החזקה ממוצעת {fmt(bt.get('avg_holding'))} ימים · "
            f"מול בנצ׳מרק {fmt(bt.get('benchmark_rel'), '%', dash='—')} · "
            f"ירידה מקס׳ {fmt(bt.get('max_drawdown'), '%')}</div>", unsafe_allow_html=True)
        rw = r.get("RiskWarnings")
        if isinstance(rw, str) and rw.strip():
            st.markdown(f"**סיכונים עיקריים:** {rw}")
        if bt["occurrences"] < 4:
            st.caption("⚠️ מדגם קטן (פחות מ‑4 מופעים) — האות לא אומת מספיק; להתייחס בזהירות.")
        st.caption("מבוסס על סימולציית עסקאות היסטוריות של אות הפריצה (כניסה באות; יציאה בשבירת "
                   "ממוצע 50 יום או עד 20 ימי מסחר), כולל אימות Out-of-Sample (30% אחרונים).")
    else:
        st.caption("אין מספיק איתותים היסטוריים למניה זו — לא ניתן לאמת את האות סטטיסטית. "
                   "להתייחס בזהירות יתרה.")

    # Fundamental metrics panel (real yfinance data; 'אין נתון' if missing).
    def _cap(v):
        if not isinstance(v, (int, float)) or v != v:
            return "אין נתון"
        for unit, div in [("T", 1e12), ("B", 1e9), ("M", 1e6)]:
            if abs(v) >= div:
                return f"${v/div:.2f}{unit}"
        return f"${v:.0f}"
    st.markdown("##### 🧮 נתונים פונדמנטליים")
    sec = r.get("Sector")
    st.caption(f"סקטור: {sec if isinstance(sec,str) and sec else 'אין נתון'} · "
               f"שווי שוק: {_cap(r.get('MarketCap'))}")
    fdefs = [("צמיחת הכנסות", "RevenueGrowth", "%"), ("צמיחת רווח למניה", "EPSGrowth", "%"),
             ("צמיחת תזרים חופשי", "FCFGrowth", "%"), ("שולי תפעול", "OperatingMargin", "%"),
             ("חוב/הון", "DebtToEquity", "x"), ("ROIC", "ROIC", "%"),
             ("PEG", "PEG", ""), ("מכפיל עתידי", "ForwardPE", "")]
    fcols = st.columns(4)
    for i, (lbl, key, suf) in enumerate(fdefs):
        fcols[i % 4].metric(lbl, fmt(r.get(key), suf, dash="אין נתון"))

    st.caption("💡 הציונים הקנייניים מחושבים מנתונים אמיתיים. פוטנציאל עלייה: "
               "מודל פנימי (מרחק משיא × ציון טכני + תנודתיות). ביטחון: הסכמת אותות + איכות נתונים + בקטסט.")
    if heads:
        st.markdown("**כותרות אחרונות:**")
        for h in heads[:5]:
            st.markdown(f"- {h['title']}  <span style='color:{MUTED}'>· {h['publisher']}</span>",
                        unsafe_allow_html=True)


# ===========================================================================
# PAGE: sectors
# ===========================================================================

elif page == "🗺️ סקטורים":
    st.markdown("### 🗺️ אינטליגנציית סקטורים")
    sectors = mkt.get("sectors", [])
    if not sectors or "score" not in sectors[0]:
        st.caption("נתוני סקטורים לא זמינים כרגע. הריצו רענון.")
    else:
        ranked = sorted(sectors, key=lambda s: s["score"], reverse=True)
        # Headline: strongest & weakest
        strong, weak = ranked[0], ranked[-1]
        h1, h2 = st.columns(2)
        h1.markdown(f"<div class='card' style='border-right:5px solid {GREEN}'>"
                    f"<div style='color:{MUTED}'>🟢 הסקטור החזק ביותר היום</div>"
                    f"<div style='font-size:24px;font-weight:800'>{strong['sector']}</div>"
                    f"<div>ציון <b style='color:{GREEN}'>{strong['score']}</b> · {strong['trend']} · "
                    f"חוזק יחסי מול S&P {strong['rs']:+}% · חודש {strong['ret_1m']:+}%</div></div>",
                    unsafe_allow_html=True)
        h2.markdown(f"<div class='card' style='border-right:5px solid {RED}'>"
                    f"<div style='color:{MUTED}'>🔴 הסקטור החלש ביותר היום</div>"
                    f"<div style='font-size:24px;font-weight:800'>{weak['sector']}</div>"
                    f"<div>ציון <b style='color:{RED}'>{weak['score']}</b> · {weak['trend']} · "
                    f"חוזק יחסי מול S&P {weak['rs']:+}% · חודש {weak['ret_1m']:+}%</div></div>",
                    unsafe_allow_html=True)

        # Heatmap by sector score
        sdf = pd.DataFrame(ranked).sort_values("score")
        colors = [GREEN if v >= 60 else (AMBER if v >= 40 else RED) for v in sdf["score"]]
        fig = go.Figure(go.Bar(x=sdf["score"], y=sdf["sector"], orientation="h",
                               marker_color=colors,
                               text=[f"{v}" for v in sdf["score"]], textposition="auto"))
        fig.update_layout(title="ציון סקטור (0–100)", xaxis_range=[0, 100])
        st.plotly_chart(style_fig(fig, 420), use_container_width=True)

        # Full ranked table
        st.markdown("##### דירוג מלא")
        table = pd.DataFrame(ranked)[["rank", "sector", "score", "trend",
                                      "momentum", "rs", "ret_1m", "ret_3m", "change_pct"]]
        table.columns = ["דירוג", "סקטור", "ציון", "מגמה", "מומנטום",
                         "חוזק יחסי %", "תשואה חודש %", "תשואה רבעון %", "יומי %"]
        st.dataframe(
            table, use_container_width=True, hide_index=True,
            column_config={
                "ציון": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
                "מומנטום": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            },
        )
        st.caption("ציון סקטור = מגמה (40%) + מומנטום חודשי (30%) + חוזק יחסי מול S&P 500 (30%). "
                   "מבוסס על ETF סקטוריאליים אמיתיים (XLK, XLF, ...).")


# ===========================================================================
# PAGE: alerts / news / backtest
# ===========================================================================

elif page == "💼 תיק":
    st.markdown("### 💼 ניהול תיק")
    pf = load_portfolio()
    st.caption("הנתונים נטענים מ‑portfolio.csv. ערוך למטה את ההחזקות שלך, או העלה CSV "
               "(עמודות: Ticker, Quantity, AverageCost).")

    if pf.get("empty"):
        st.info("אין החזקות עדיין. הוסף שורות בטבלה למטה ולחץ 'שמור והרץ'.")
    else:
        # --- Section 1: Executive KPI strip ---
        bm = pf.get("benchmark", {})
        prisk = pf.get("risk", {})
        h = pf.get("health", {})
        hs = h.get("score")
        dch = pf.get("daily_change_pct", 0) or 0
        wbeta = prisk.get("weighted_beta")
        effn = prisk.get("effective_positions")
        conc = prisk.get("concentration_risk")
        beta_c = NEGATIVE if isinstance(wbeta, (int, float)) and wbeta > 1.2 else POSITIVE
        conc_c = (NEGATIVE if isinstance(conc, (int, float)) and conc >= 66
                  else WARNING if isinstance(conc, (int, float)) and conc >= 40 else POSITIVE)
        kp = [
            kpi_html(PRIMARY, "💰", f"${pf['total_value']:,.0f}", "שווי תיק",
                     f"רווח כולל {pf['total_pl_pct']:+.1f}%", "שווי שוק נוכחי של ההחזקות"),
            kpi_html(POSITIVE if dch >= 0 else NEGATIVE, "📅", f"{dch:+.2f}%", "שינוי יומי",
                     f"מול S&P {bm.get('daily', 0):+.2f}%", "שינוי יומי מול הבנצ׳מרק"),
            kpi_html(score_color(hs), "🩺", fmt(hs), "בריאות תיק", "פיזור · ריכוז · סיכון",
                     "ציון בריאות התיק 0-100"),
            kpi_html(beta_c, "📊", fmt(wbeta), "ביתא תיק", "רגישות לשוק",
                     "ביתא משוקללת מול S&P 500"),
            kpi_html(POSITIVE if isinstance(effn, (int, float)) and effn >= 4 else WARNING, "🧩",
                     fmt(effn), "פיזור", "פוזיציות אפקטיביות", "1/HHI — כמה פוזיציות שקולות זה למעשה"),
            kpi_html(conc_c, "🎯", fmt(conc), "ריכוז", "0=מפוזר · 100=מרוכז", "ציון ריכוז התיק 0-100"),
        ]
        st.markdown(f"<div class='kpi-grid'>{''.join(kp)}</div>", unsafe_allow_html=True)

        # --- Section 2: Allocation + health ---
        st.markdown("#### 📊 הקצאה ובריאות")
        _donut = [PRIMARY, POSITIVE, WARNING, NEGATIVE, "#a78bfa", "#f472b6", "#22d3ee"]
        cc = st.columns([1.1, 1, 1])
        with cc[0]:
            exp_s = pf["exposures"].get("sector", {})
            if exp_s:
                fig = go.Figure(go.Pie(labels=list(exp_s.keys()), values=list(exp_s.values()),
                                       hole=0.58, marker=dict(colors=_donut)))
                fig.update_traces(textinfo="label+percent", textfont_size=11)
                fig.update_layout(title="הקצאה לפי סקטור", showlegend=False)
                st.plotly_chart(style_fig(fig, 250), use_container_width=True)
        with cc[1]:
            exp_r = pf["exposures"].get("risk", {})
            if exp_r:
                fig = go.Figure(go.Pie(labels=list(exp_r.keys()), values=list(exp_r.values()),
                                       hole=0.58, marker=dict(colors=[POSITIVE, WARNING, NEGATIVE, "#7f1d1d"])))
                fig.update_traces(textinfo="label+percent", textfont_size=11)
                fig.update_layout(title="חשיפה לפי סיכון", showlegend=False)
                st.plotly_chart(style_fig(fig, 250), use_container_width=True)
        with cc[2]:
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=hs or 0,
                number={"font": {"color": score_color(hs), "size": 34}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": score_color(hs), "thickness": 0.3},
                       "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
                       "steps": [{"range": [0, 40], "color": "#2a1320"},
                                 {"range": [40, 66], "color": "#2c2a12"},
                                 {"range": [66, 100], "color": "#0f2e1c"}]}))
            style_fig(fig, 250)
            fig.update_layout(title="בריאות תיק")
            st.plotly_chart(fig, use_container_width=True)
        if h.get("factors"):
            st.caption(" · ".join(h["factors"]))

        # --- Section 3: Risk contribution + correlation ---
        st.markdown("#### 🛡️ תרומת סיכון וקורלציות")
        rcc = st.columns(2)
        posdf = pd.DataFrame(pf["positions"])
        with rcc[0]:
            if {"ticker", "weight", "beta"}.issubset(posdf.columns):
                rd = posdf.dropna(subset=["beta"]).copy()
                rd["contrib"] = (rd["weight"] / 100.0 * rd["beta"]).round(3)
                rd = rd.sort_values("contrib")
                bcol = [NEGATIVE if v > 0.3 else (WARNING if v > 0.15 else POSITIVE) for v in rd["contrib"]]
                fig = go.Figure(go.Bar(x=rd["contrib"], y=rd["ticker"], orientation="h",
                                       marker_color=bcol,
                                       text=[f"{v:.2f}" for v in rd["contrib"]], textposition="auto"))
                fig.update_layout(title="תרומת סיכון (משקל × ביתא)")
                st.plotly_chart(style_fig(fig, 300), use_container_width=True)
                st.caption("אומדן תרומת כל החזקה לסיכון התיק = משקל × ביתא.")
        with rcc[1]:
            corr = pf.get("correlation", {}).get("matrix", {})
            if corr and len(corr) >= 2:
                tk = list(corr.keys())
                z = [[corr[a].get(b, 0) for b in tk] for a in tk]
                fig = go.Figure(go.Heatmap(z=z, x=tk, y=tk, zmin=-1, zmax=1, colorscale="RdYlGn_r",
                                           text=z, texttemplate="%{text:.2f}", textfont_size=10))
                fig.update_layout(title="מטריצת קורלציה (תשואות יומיות)")
                st.plotly_chart(style_fig(fig, 300), use_container_width=True)

        # --- Section 4: Highlights — concentration / hidden corr / actions ---
        hi = st.columns(3)
        warns = prisk.get("warnings", [])
        hi[0].markdown(f"<div class='card' style='border-right:5px solid {NEGATIVE}'>"
                       f"<div class='ic-title'>🎯 ריכוזים</div>" +
                       ("".join(f"<div class='ic-sub'>⚠️ {w}</div>" for w in warns)
                        or "<div class='ic-sub'>אין ריכוז חריג</div>") + "</div>", unsafe_allow_html=True)
        hp = pf.get("correlation", {}).get("high_pairs", [])
        hi[1].markdown(f"<div class='card' style='border-right:5px solid {WARNING}'>"
                       f"<div class='ic-title'>🔗 קורלציות סמויות</div>" +
                       ("".join(f"<div class='ic-sub'>{p['a']}–{p['b']} ({p['corr']})</div>" for p in hp)
                        or "<div class='ic-sub'>אין זוגות מתואמים גבוה</div>") + "</div>", unsafe_allow_html=True)
        today_acts = (pf.get("decisions") or {}).get("today", [])[:4]
        hi[2].markdown(f"<div class='card' style='border-right:5px solid {PRIMARY}'>"
                       f"<div class='ic-title'>✅ פעולות מוצעות</div>" +
                       ("".join(f"<div class='ic-sub'>{a}</div>" for a in today_acts)
                        or "<div class='ic-sub'>אין פעולות</div>") + "</div>", unsafe_allow_html=True)

        # --- Holdings table ---
        st.markdown("##### 📋 החזקות")
        pos = pd.DataFrame(pf["positions"])
        cols = ["ticker", "name", "quantity", "avg_cost", "price", "market_value",
                "pl", "pl_pct", "weight", "beta", "volatility", "sector"]
        view = pos[[c for c in cols if c in pos.columns]].copy()
        view.columns = ["סימול", "שם", "כמות", "מחיר ממוצע", "מחיר נוכחי",
                        "שווי שוק", "רווח/הפסד", "רווח %", "משקל %", "ביתא", "תנודתיות", "סקטור"][:len(view.columns)]
        st.dataframe(view, use_container_width=True, hide_index=True, column_config={
            "מחיר ממוצע": st.column_config.NumberColumn(format="$%.2f"),
            "מחיר נוכחי": st.column_config.NumberColumn(format="$%.2f"),
            "שווי שוק": st.column_config.NumberColumn(format="$%.0f"),
            "רווח/הפסד": st.column_config.NumberColumn(format="$%.0f"),
            "רווח %": st.column_config.NumberColumn(format="%.1f%%"),
            "משקל %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
        })

        # --- Portfolio alerts ---
        if pf.get("alerts"):
            st.markdown("##### 🔔 התראות תיק")
            for a in pf["alerts"]:
                col = RED if a["severity"] == "גבוהה" else AMBER
                st.markdown(f"<div class='card' style='border-right:4px solid {col};padding:8px 12px'>"
                            f"<b style='color:{col}'>{a['scope']}</b> · {a['message']}</div>",
                            unsafe_allow_html=True)

    # --- Edit holdings ---
    st.divider()
    st.markdown("##### ✏️ עריכת החזקות")
    current = pd.read_csv(config.PORTFOLIO_CSV) if os.path.exists(config.PORTFOLIO_CSV) \
        else pd.DataFrame(columns=["Ticker", "Quantity", "AverageCost"])
    edited = st.data_editor(current, num_rows="dynamic", use_container_width=True,
                            key="pf_editor")
    cc = st.columns([1, 1, 3])
    if cc[0].button("💾 שמור והרץ", use_container_width=True):
        edited.to_csv(config.PORTFOLIO_CSV, index=False, encoding="utf-8-sig")
        with st.spinner("מחשב תיק מחדש…"):
            try:
                run_scan(); ok = True
            except Exception:
                ok = False
        st.cache_data.clear()
        st.success("נשמר ועודכן!") if ok else st.error("העדכון נכשל.")
        st.rerun()
    up = cc[1].file_uploader("📤 ייבוא CSV", type=["csv"], label_visibility="collapsed")
    if up is not None:
        try:
            imp = pd.read_csv(up)
            imp.to_csv(config.PORTFOLIO_CSV, index=False, encoding="utf-8-sig")
            st.success("הקובץ יובא! לחץ 'שמור והרץ' לעדכון.")
        except Exception as exc:
            st.error(f"ייבוא נכשל: {exc}")

elif page == "🧭 החלטות תיק":
    st.markdown("### 🧭 החלטות תיק — מנוע החלטות")
    pf = load_portfolio()
    dec = pf.get("decisions", {})
    if pf.get("empty") or not dec:
        st.info("אין החזקות/החלטות. הוסף החזקות בטאב 💼 תיק ולחץ 'שמור והרץ'.")
    else:
        averb = {"Increase": "🟢 הגדל", "Hold": "🔵 החזק", "Reduce": "🟡 הקטן", "Exit": "🔴 צא"}
        H = dec["holdings"]

        st.markdown("#### 📌 מה לעשות היום?")
        for a in (dec.get("today") or ["אין פעולות נדרשות היום."]):
            st.markdown(f"- {a}")

        if dec.get("constraints"):
            st.markdown("#### ⚠️ אילוצים שנפרצו")
            for c in dec["constraints"]:
                st.markdown(f"<div class='card' style='border-right:4px solid {RED};padding:8px 12px'>"
                            f"{c}</div>", unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 📊 הקצאה: נוכחית מול מומלצת")
        tk = [h["ticker"] for h in H]
        fig = go.Figure()
        fig.add_bar(name="נוכחי", x=tk, y=[h["current_pct"] for h in H], marker_color=BLUE)
        fig.add_bar(name="מומלץ", x=tk, y=[h["target_pct"] for h in H], marker_color=GREEN)
        fig.update_layout(barmode="group", yaxis_title="% מהתיק")
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)

        rows = [{"סימול": h["ticker"], "פעולה": averb[h["action"]], "כעת %": h["current_pct"],
                 "יעד %": h["target_pct"], "עדיפות": h["priority"], "ביטחון": h["confidence"],
                 "v2": h["score_v2"], "שווי": h.get("valuation"), "סיכון": h["risk_level"],
                 "השפעת סיכון": h["risk_impact"]} for h in H]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, column_config={
            "ביטחון": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "v2": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "שווי": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")})

        st.markdown("#### 🔎 הסבר לכל החלטה (Why / נתונים / סיכונים)")
        for h in H:
            with st.expander(f"{averb[h['action']]} · {h['ticker']} — {h['name']}  "
                             f"(כעת {h['current_pct']}% → יעד {h['target_pct']}%)"):
                st.markdown(f"**למה:** {h['reasoning']}")
                st.markdown("**נתונים תומכים:** " + " · ".join(h["why"]))
                st.markdown("**סיכונים שנותרו:** " + " · ".join(h["risks"]))

        st.divider()
        st.markdown("#### ⚖️ איזון מחדש")
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("**סקטורים בעודף משקל**")
            ow = dec.get("overweight_sectors", [])
            for s in ow:
                st.markdown(f"- {s['sector']} ({s['weight']}%) — {s['reason']}")
            if not ow:
                st.caption("אין עודף משקל סקטוריאלי.")
        with rc2:
            st.markdown("**סקטורים חזקים בחוסר משקל**")
            uw = dec.get("underweight_sectors", [])
            for s in uw:
                st.markdown(f"- {s['sector']} (ציון {s['score']}, כעת {s['weight']}%)")
            if not uw:
                st.caption("אין.")
        if dec.get("risk_actions"):
            st.markdown("**🛡️ פעולות הפחתת סיכון**")
            for a in dec["risk_actions"]:
                st.markdown(f"- {a}")
        st.caption("כל החלטה מבוססת על ScoreV2 + סיכון + חוזק סקטור + ריכוז + קורלציה + מצב שוק. "
                   "לעולם לא ממליץ על ריכוז. לצרכי מידע בלבד, לא ייעוץ.")

elif page == "🛡️ אמון ואימות":
    st.markdown("### 🛡️ אמון ואימות")
    sh = load_system_health()
    bt_all = load_backtest()

    st.markdown("#### 🩺 בריאות מערכת")
    c = st.columns(6)
    c[0].metric("מניות נסרקו", sh.get("scanned", "—"))
    c[1].metric("איתותים", sh.get("signals", "—"))
    c[2].metric("שלמות נתונים", f"{sh.get('data_completeness', '—')}%")
    c[3].metric("משיכות שנכשלו", sh.get("failed_pulls", "—"))
    c[4].metric("ביטחון ממוצע", sh.get("avg_confidence", "—"))
    c[5].metric("אמון ממוצע", sh.get("avg_trust", "—"))
    sd = sh.get("sector_distribution", {})
    if sd:
        fig = go.Figure(go.Bar(x=list(sd.values()), y=list(sd.keys()),
                               orientation="h", marker_color=BLUE))
        fig.update_layout(title="התפלגות הזדמנויות לפי סקטור")
        st.plotly_chart(style_fig(fig, 240), use_container_width=True)

    st.divider()
    st.markdown("#### 📋 אמון לכל מניה")
    emap = {"גבוה": "🟢", "בינוני": "🟡", "נמוך": "🔴"}
    rows = []
    for _, r in df.sort_values("TrustScore", ascending=False).iterrows():
        sr = trust_engine.signal_reliability(r, bt_all.get(r["Ticker"]))
        rows.append({"סימול": r["Ticker"], "אמון": int(r["TrustScore"]),
                     "רמה": f"{emap.get(r['TrustCategory'], '')} {r['TrustCategory']}",
                     "ScoreV2": int(r["ScoreV2"]), "ביטחון": sr["confidence"],
                     "הצלחה היסט׳": sr["hist_win_rate"], "מופעים": sr["occurrences"],
                     "עודף מול S&P": sr["excess_return"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, column_config={
        "אמון": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        "ScoreV2": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        "הצלחה היסט׳": st.column_config.NumberColumn(format="%.0f%%"),
        "עודף מול S&P": st.column_config.NumberColumn(format="%.1f%%")})

    st.divider()
    st.markdown("#### 🔬 פירוט אמון למניה")
    sym = st.selectbox("בחר מניה", df["Ticker"].tolist(), key="trust_sym")
    r = df[df["Ticker"] == sym].iloc[0]
    ti = trust_engine.trust_score(r, bt_all.get(sym))
    sr = trust_engine.signal_reliability(r, bt_all.get(sym))
    g1, g2 = st.columns([1, 2])
    with g1:
        col = {"גבוה": GREEN, "בינוני": AMBER, "נמוך": RED}.get(ti["category"], MUTED)
        st.markdown(f"**ציון אמון: {emap.get(ti['category'], '')} {ti['category']}**")
        fig = go.Figure(go.Indicator(mode="gauge+number", value=ti["score"],
                                     number={"font": {"color": TEXT}},
                                     gauge={"axis": {"range": [0, 100]}, "bar": {"color": col}}))
        st.plotly_chart(style_fig(fig, 200), use_container_width=True)
    with g2:
        m = st.columns(3)
        m[0].metric("ביטחון", sr["confidence"])
        m[1].metric("הצלחה היסט׳", fmt(sr["hist_win_rate"], "%", dash="—"))
        m[2].metric("מופעים", fmt(sr["occurrences"], dash="—"))
        m2 = st.columns(3)
        m2[0].metric("תשואה ממוצעת", fmt(sr["avg_return"], "%", dash="—"))
        m2[1].metric("עודף מול S&P", fmt(sr["excess_return"], "%", dash="—"))
        m2[2].metric("ירידה מקס׳", fmt(sr["max_drawdown"], "%", dash="—"))
    e1, e2 = st.columns(2)
    with e1:
        st.markdown("**✅ למה לסמוך על ההמלצה?**")
        for s in ti["strengths"]:
            st.markdown(f"- {s}")
    with e2:
        st.markdown("**⚠️ למה להיזהר?**")
        for lim in ti["limitations"]:
            st.markdown(f"- {lim}")
    with st.expander("פירוק ציון האמון (7 גורמים)"):
        flabels = {"data_quality": "איכות נתונים", "historical_validation": "אימות היסטורי",
                   "sample_size": "גודל מדגם", "out_of_sample": "Out-of-Sample",
                   "fundamental_completeness": "שלמות פונדמנטלית",
                   "score_consistency": "עקביות ציונים", "risk_model": "מודל סיכון"}
        for k, v in ti["factors"].items():
            st.markdown(f"- {flabels.get(k, k)}: {v} נק׳")

    st.divider()
    st.markdown("#### ⚠️ מגבלות ידועות של המערכת")
    for lim in ["מקור נתונים יחיד (Yahoo Finance) — ללא גיבוי",
                "בסורק השוק מועשרות רק Top-40 (לא כל היקום)",
                "בקטסט במדגם קטן לחלק מהמניות — אימות מוגבל",
                "סנטימנט חדשות מבוסס מילון בסיסי",
                "Russell 2000 לא נכלל ביקום",
                "לצרכי מידע בלבד — לא ייעוץ השקעות"]:
        st.markdown(f"- {lim}")
    st.info("הדאשבורד עונה: **מה ההזדמנויות** (🏠/🔭) · **כמה לסמוך** (כאן) · "
            "**אילו ראיות** (📊 בקטסט) · **אילו סיכונים** (🔔/🛡️).")

elif page == "🔔 התראות":
    st.markdown("### 🔔 מרכז התראות")
    center = load_alert_center()
    if not center:
        st.caption("אין התראות פעילות כרגע.")
    else:
        sev_color = {"גבוהה": RED, "בינונית": AMBER, "מידע": BLUE}
        type_icon = {"פריצה": "🚀", "זינוק נפח": "📊", "דוחות": "📅",
                     "שינוי דירוג": "🏦", "אזהרת סיכון": "⚠️", "רוטציית סקטורים": "🔄"}
        # Summary counts by type
        from collections import Counter
        counts = Counter(a["type"] for a in center)
        st.caption(" · ".join(f"{type_icon.get(t,'•')} {t}: {c}" for t, c in counts.items()))
        st.divider()
        for a in center:
            col = sev_color.get(a["severity"], MUTED)
            st.markdown(
                f"<div class='card' style='border-right:5px solid {col};padding:10px 14px'>"
                f"<span style='font-weight:700'>{type_icon.get(a['type'],'🔔')} {a['type']}</span> "
                f"<span style='color:{col};font-size:12px'>· {a['severity']}</span> "
                f"<span style='color:{MUTED};font-size:12px'>· {a['scope']}</span><br>"
                f"<span style='color:{TEXT}'>{a['message']}</span></div>",
                unsafe_allow_html=True)

elif page == "📰 חדשות":
    st.markdown("#### 📰 חדשות אחרונות (מניות מובילות)")
    for _, r in (positive.head(6) if not positive.empty else df.head(6)).iterrows():
        heads, sent = get_news_sentiment(r["Ticker"])
        tone = GREEN if sent["score"] >= 60 else (RED if sent["score"] <= 40 else AMBER)
        st.markdown(f"<div class='card'><b>{r['Ticker']}</b> — {r['Name']} "
                    f"<span style='color:{tone}'>· סנטימנט {sent['score']}</span></div>",
                    unsafe_allow_html=True)
        for h in heads[:3]:
            st.markdown(f"- {h['title']}  <span style='color:{MUTED}'>· {h['publisher']}</span>",
                        unsafe_allow_html=True)

elif page == "📊 בקטסט":
    st.markdown("#### 📊 ביצועי אות הפריצה בעבר (Backtest אמיתי)")
    _, backtest = read_outputs()
    if backtest.empty:
        st.caption("אין נתוני בקטסט.")
    else:
        st.dataframe(backtest, use_container_width=True, hide_index=True)
        st.caption("אחוז הצלחה = שיעור האיתותים שהניבו תשואה חיובית בטווח שנמדד.")

elif page == "🔎 ניתוח חברה":
    import deepdive
    from deepdive_report import to_html
    from indicators.technical import rsi as _rsi

    st.markdown("### 🔎 ניתוח חברה — Company Deep Dive")
    st.caption("הזן סימול מניה לקבלת ניתוח השקעה מלא. נתונים חיים מ-Yahoo Finance · " + deepdive.DISCLAIMER)
    q = st.columns([2, 1, 4])
    tkin = q[0].text_input("סימול", value="AAPL", label_visibility="collapsed",
                           placeholder="לדוגמה: NVDA, AAPL, LLY, PLTR").strip().upper()
    q[1].button("🔎 נתח", use_container_width=True)
    q[2].caption("דוגמאות: NVDA · AAPL · LLY · PLTR · MSFT · GOOGL")

    if tkin:
        with st.spinner(f"מנתח את {tkin}…"):
            try:
                bundle = deepdive_fetch(tkin)
                rep = deepdive.analyze(tkin, sectors=mkt.get("sectors"), bundle=bundle)
            except Exception as e:
                rep = {"error": f"שגיאה בניתוח {tkin}: {e}"}
        if rep.get("error"):
            st.error(rep["error"])
        else:
            o, md, fin = rep["overview"], rep["market_data"], rep["financials"]
            val, sc, tech, rk = rep["valuation"], rep["scores"], rep["technicals"], rep["risk"]
            op, pc, th = rep["opinion"], rep["pros_cons"], rep["thesis"]
            hist = bundle.get("hist")

            # ---- Summary card (Hebrew description, larger & clearer) ----
            desc_he = o.get("summary_he")
            sec_line = f"{o['sector_he']} · {o['industry']} · {o.get('geography','')}"
            if desc_he:
                body = (f"<div style='color:{TEXT};font-size:16px;line-height:1.95;margin-top:12px'>{desc_he}</div>"
                        f"<div class='ic-sub' style='margin-top:8px'>תורגם אוטומטית מאנגלית · המקור המלא למטה</div>")
            else:
                body = (f"<div style='color:{TEXT};font-size:16px;line-height:1.95;margin-top:12px'>{o.get('he_line','')}</div>"
                        f"<div class='ic-sub' style='margin-top:8px'>תרגום אוטומטי לא זמין כרגע — התיאור המלא באנגלית למטה</div>")
            st.markdown(f"<div class='ic-card'>"
                        f"<div class='ic-title' style='font-size:24px'>{o['name']} "
                        f"<span style='color:{MUTED};font-size:16px'>· {tkin}</span></div>"
                        f"<div class='ic-sub' style='font-size:15px'>{sec_line}</div>"
                        f"{body}</div>", unsafe_allow_html=True)
            if isinstance(o["summary"], str) and o["summary"] != NA_:
                with st.expander("📄 תיאור מקורי (אנגלית)"):
                    st.write(o["summary"])

            # ---- KPI strip ----
            v2 = sc["final_v2"]["value"]
            r1y = _num_or(md["ret_1y"])
            kk = [
                kpi_html(PRIMARY, "💵", md["price"], "מחיר", md["daily_change"], "מחיר נוכחי ושינוי יומי"),
                kpi_html(PRIMARY, "🏦", md["market_cap"], "שווי שוק", o["sector"], "שווי שוק"),
                kpi_html(POSITIVE if (r1y or 0) >= 0 else NEGATIVE, "📈", md["ret_1y"], "תשואה שנה", f"3ח' {md['ret_3m']}", "תשואת 12 חודשים"),
                kpi_html(score_color(v2), "🎯", v2, "ציון סופי v2", "משוקלל", "הציון המשוקלל של המערכת"),
                kpi_html(score_color(sc["trust"]["value"]), "🛡️", sc["trust"]["value"], "ציון אמון", sc["trust"]["category"], "כמה לסמוך על הניתוח"),
                kpi_html(NEGATIVE if (rk["risk_score"] or 0) >= 66 else (WARNING if (rk["risk_score"] or 0) >= 33 else POSITIVE), "⚠️", rk["risk_score"], "ציון סיכון", rk["category"], "גבוה = מסוכן יותר"),
            ]
            st.markdown(f"<div class='kpi-grid'>{''.join(kk)}</div>", unsafe_allow_html=True)

            # ---- Returns strip ----
            rets = [("שבוע", md["ret_1w"]), ("חודש", md["ret_1m"]), ("3 ח'", md["ret_3m"]),
                    ("6 ח'", md["ret_6m"]), ("YTD", md["ytd"]), ("שנה", md["ret_1y"]), ("3 שנים", md["ret_3y"])]
            chips = "".join(f"<span style='margin-left:18px'><b style='color:{MUTED}'>{lbl}</b> "
                            f"<b style='color:{POSITIVE if (_num_or(v) or 0)>=0 else NEGATIVE}'>{v}</b></span>" for lbl, v in rets)
            st.markdown(f"<div class='ic-card' style='padding:12px 18px'>{chips}</div>", unsafe_allow_html=True)

            # ---- Price chart with MAs + support/resistance ----
            if hist is not None and "Close" in hist.columns:
                c = hist["Close"].dropna().tail(252)
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=c.values, x=list(range(len(c))), name="מחיר", line_color=PRIMARY))
                for n, col in [(20, WARNING), (50, "#a78bfa"), (200, MUTED)]:
                    if len(c) >= n:
                        fig.add_trace(go.Scatter(y=c.rolling(n).mean().values, x=list(range(len(c))),
                                                 name=f"MA{n}", line=dict(width=1.3, color=col)))
                sr = tech["support_resistance"]
                if sr.get("support"):
                    fig.add_hline(y=sr["support"], line_dash="dot", line_color=POSITIVE,
                                  annotation_text=f"תמיכה {sr['support']}")
                if sr.get("resistance"):
                    fig.add_hline(y=sr["resistance"], line_dash="dot", line_color=NEGATIVE,
                                  annotation_text=f"התנגדות {sr['resistance']}")
                fig.update_layout(title=f"{tkin} · מחיר + ממוצעים נעים (שנה)")
                st.plotly_chart(style_fig(fig, 320), use_container_width=True)

                # Volume / RSI / MACD
                ch = st.columns(3)
                vv = hist["Volume"].dropna().tail(120)
                fv = go.Figure(go.Bar(y=vv.values, x=list(range(len(vv))), marker_color=PRIMARY))
                fv.update_layout(title="נפח מסחר (120 ימים)")
                ch[0].plotly_chart(style_fig(fv, 220), use_container_width=True)

                rsis = _rsi(c, 14).dropna().tail(180)
                fr = go.Figure(go.Scatter(y=rsis.values, x=list(range(len(rsis))), line_color=WARNING))
                fr.add_hline(y=70, line_dash="dot", line_color=NEGATIVE)
                fr.add_hline(y=30, line_dash="dot", line_color=POSITIVE)
                fr.update_layout(title="RSI(14)", yaxis_range=[0, 100])
                ch[1].plotly_chart(style_fig(fr, 220), use_container_width=True)

                mser = tech["macd"].get("_series")
                if mser:
                    ml, sg, hh = mser["macd"].tail(180), mser["signal"].tail(180), mser["hist"].tail(180)
                    fm = go.Figure()
                    fm.add_trace(go.Bar(y=hh.values, x=list(range(len(hh))), name="היסטוגרמה",
                                        marker_color=[POSITIVE if v >= 0 else NEGATIVE for v in hh.values]))
                    fm.add_trace(go.Scatter(y=ml.values, x=list(range(len(ml))), name="MACD", line_color=PRIMARY))
                    fm.add_trace(go.Scatter(y=sg.values, x=list(range(len(sg))), name="Signal", line_color=WARNING))
                    fm.update_layout(title="MACD")
                    ch[2].plotly_chart(style_fig(fm, 220), use_container_width=True)

            # ---- Financials + Valuation tables ----
            def _tbl(rows):
                return "<table style='width:100%;border-collapse:collapse'>" + "".join(
                    f"<tr><td style='color:{MUTED};padding:7px 8px;border-bottom:1px solid {BORDER};font-size:14.5px'>{k}</td>"
                    f"<td style='text-align:left;padding:7px 8px;border-bottom:1px solid {BORDER};font-weight:600;font-size:14.5px'>{v}</td></tr>"
                    for k, v in rows) + "</table>"
            fcol = st.columns(2)
            fcol[0].markdown("#### 💰 דוחות כספיים")
            fcol[0].markdown("<div class='ic-card'>" + _tbl([
                ("הכנסות", fin["revenue"]), ("צמיחת הכנסות", fin["revenue_growth"]),
                ("רווח גולמי / שולי", f"{fin['gross_profit']} · {fin['gross_margin']}"),
                ("רווח תפעולי / שולי", f"{fin['operating_income']} · {fin['operating_margin']}"),
                ("רווח נקי / שולי", f"{fin['net_income']} · {fin['net_margin']}"),
                ("רווח למניה / צמיחה", f"{fin['eps']} · {fin['eps_growth']}"),
                ("FCF / שולי", f"{fin['fcf']} · {fin['fcf_margin']}"),
                ("חוב / מזומן", f"{fin['debt']} · {fin['cash']}"),
                ("חוב/הון · ROE · ROIC", f"{fin['debt_to_equity']} · {fin['roe']} · {fin['roic']}"),
            ]) + "</div>", unsafe_allow_html=True)
            fcol[1].markdown("#### ⚖️ תמחור")
            vcolor = score_color(val["score"])
            fcol[1].markdown(f"<div class='ic-card'>" + _tbl([
                ("מכפיל עתידי", val["forward_pe"]), ("מכפיל נוכחי", val["trailing_pe"]),
                ("PEG", val["peg"]), ("מחיר/מכירות", val["price_sales"]),
                ("EV/EBITDA", val["ev_ebitda"]), ("מחיר/FCF", val["price_fcf"]),
            ]) + f"<div style='margin-top:10px;font-weight:800;color:{vcolor}'>{val['label']}</div></div>",
                unsafe_allow_html=True)

            # ---- Score breakdown ----
            st.markdown("#### 🎯 ציוני Stock Agent")
            rh = sc["risk"]["value"]
            bars = (score_bar("ציון סופי v2", v2) + score_bar("טכני", sc["technical"]["value"])
                    + score_bar("פונדמנטלי", _num_or(sc["fundamental"]["value"]))
                    + score_bar("סקטור", _num_or(sc["sector"]["value"]))
                    + score_bar("חדשות", _num_or(sc["news"]["value"]))
                    + score_bar("ניהול סיכון", (None if not isinstance(rh, (int, float)) else 100 - rh))
                    + score_bar("אמון", sc["trust"]["value"]))
            st.markdown(f"<div class='ic-card'>{bars}<div class='ic-sub' style='margin-top:8px'>{sc['final_v2']['explain']}</div></div>",
                        unsafe_allow_html=True)

            # ---- Technical analysis ----
            st.markdown("#### 📐 ניתוח טכני")
            ma = tech["moving_averages"]
            tsub = tech["sub_scores"]
            tc = st.columns([1.3, 1])
            tc[0].markdown(f"<div class='ic-card'>"
                           f"<div>מגמה: <b style='color:{PRIMARY}'>{tech['trend']}</b> · מומנטום: <b>{tech['momentum']}</b> · "
                           f"RSI: <b>{tech['rsi']}</b> · ATR: <b>{tech['atr']}</b> · Cross: <b>{tech['cross']}</b></div>"
                           f"<div class='ic-sub' style='margin-top:6px'>MA20 {ma['ma20']} · MA50 {ma['ma50']} · "
                           f"MA100 {ma['ma100']} · MA200 {ma['ma200']}</div>"
                           f"<div class='ic-sub'>תמיכה {_disp(tech['support_resistance'].get('support'))} · "
                           f"התנגדות {_disp(tech['support_resistance'].get('resistance'))} · "
                           f"מרחק משיא {_disp(tech['high_low'].get('dist_from_high'))}%</div>"
                           f"<div style='margin-top:8px;color:{TEXT};font-size:13px;line-height:1.6'>{tech['opinion']}</div></div>",
                           unsafe_allow_html=True)
            tc[1].markdown("<div class='ic-card'>" + score_bar("מגמה", tsub["trend"]) + score_bar("מומנטום", tsub["momentum"])
                           + score_bar("נפח", tsub["volume"]) + score_bar("תנודתיות (רגוע=גבוה)", tsub["volatility"]) + "</div>",
                           unsafe_allow_html=True)

            # ---- Thesis ----
            st.markdown("#### 🧠 תזת השקעה")
            tt = st.columns(3)
            for col, key, lbl, color in [(tt[0], "bull", "🟢 תרחיש שורי", POSITIVE),
                                         (tt[1], "base", "🔵 תרחיש בסיס", PRIMARY),
                                         (tt[2], "bear", "🔴 תרחיש דובי", NEGATIVE)]:
                col.markdown(f"<div class='ic-card' style='border-right:5px solid {color}'>"
                             f"<div class='ic-title' style='color:{color}'>{lbl}</div>"
                             f"<div class='ic-sub'>{th[key]}</div></div>", unsafe_allow_html=True)

            # ---- Pros / Cons ----
            pcc = st.columns(2)
            pcc[0].markdown(f"<div class='ic-card' style='border-right:5px solid {POSITIVE}'>"
                            f"<div class='ic-title' style='color:{POSITIVE}'>✅ למה להשקיע</div>"
                            + "".join(f"<div class='ic-sub'>• {x}</div>" for x in pc["pros"]) + "</div>", unsafe_allow_html=True)
            pcc[1].markdown(f"<div class='ic-card' style='border-right:5px solid {NEGATIVE}'>"
                            f"<div class='ic-title' style='color:{NEGATIVE}'>⚠️ למה לא</div>"
                            + "".join(f"<div class='ic-sub'>• {x}</div>" for x in pc["cons"]) + "</div>", unsafe_allow_html=True)

            # ---- Competitive / Regulation (honest) ----
            cr = st.columns(2)
            cr[0].markdown(f"<div class='ic-card'><div class='ic-title'>🏰 מיצוב תחרותי</div>"
                           f"<div class='ic-sub'>{rep['competitive']['note']}</div></div>", unsafe_allow_html=True)
            cr[1].markdown(f"<div class='ic-card'><div class='ic-title'>⚖️ רגולציה וסיכוני סקטור</div>"
                           f"<div class='ic-sub'>{rep['regulation_risks']['label']}</div>"
                           + "".join(f"<div class='ic-sub'>• {x}</div>" for x in rep['regulation_risks']['sector_risks'])
                           + "</div>", unsafe_allow_html=True)

            # ---- Final opinion ----
            st.markdown("#### 🏁 דעה סופית")
            st.markdown(f"<div class='ic-card' style='border-right:6px solid {PRIMARY}'>"
                        f"<div style='font-size:24px;font-weight:800;color:{PRIMARY}'>{op['recommendation']}</div>"
                        f"<div style='margin-top:6px'>{op['attractive']}</div>"
                        f"<div class='ic-sub' style='margin-top:6px'>טווח הקצאה מוצע: <b style='color:{TEXT}'>{op['allocation_pct']}%</b> · "
                        f"פרופיל משקיע: {op['investor_profile']}</div>"
                        f"<div class='ic-sub'>מה ישנה את ההמלצה: {op['what_changes']}</div></div>", unsafe_allow_html=True)

            # ---- Export ----
            st.download_button("📥 הורד דוח HTML", data=to_html(rep),
                               file_name=f"deepdive_{tkin}.html", mime="text/html")
            st.caption("עובדות: Yahoo Finance · ציונים: מנועי המערכת · תזה/דעה: מבוססת כללים על נתונים אמיתיים. "
                       + deepdive.DISCLAIMER)

st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")
