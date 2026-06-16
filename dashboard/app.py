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
    ["🏠 ראשי", "🔎 ניתוח חברה", "💎 הזדמנויות", "🗺️ סקטורים", "🚨 התראות",
     "📊 אינטליגנציית שוק", "⚙️ הגדרות"],
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
    alerts = load_alert_center()
    health = load_system_health()

    # ---------- Section 1: Executive KPI strip ----------
    reg_s, reg_l = regime.get("score"), regime.get("label", "—")
    fg_s, fg_l = fng.get("score"), fng.get("label", "")
    fg_c = (NEGATIVE if isinstance(fg_s, (int, float)) and fg_s < 45
            else POSITIVE if isinstance(fg_s, (int, float)) and fg_s > 55 else WARNING)
    crit = [a for a in alerts if a.get("severity") in ("קריטית", "גבוהה")]
    br_score = (breadth or {}).get("score")
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
        _kpi(score_color(br_score), "🌐", fmt(br_score), "רוחב שוק", "% מהמניות במגמה",
             "מדד רוחב שוק 0-100 — כמה מהמניות במגמה חיובית"),
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
        st.markdown("#### 💎 הזדמנויות לבחינה היום")
        top3 = (positive if not positive.empty else df).sort_values("ScoreV2", ascending=False).head(3)
        grid = "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:12px'>"
        for i, (_, r) in enumerate(top3.iterrows(), start=1):
            info = classify(r)
            grid += (f"<div class='act' style='--ac:{info['color']}'><div class='a-pr'>🎯 עדיפות {i}</div>"
                     f"<div class='a-ti'>בחן {r['Ticker']}</div>"
                     f"<div class='a-row'><b>למה:</b> {info['summary']}</div>"
                     f"<div class='a-row'><b>ציון V2:</b> {int(r['ScoreV2'])} · <b>סיכון:</b> {fmt(r.get('RiskLevel'))} · "
                     f"<b>ביטחון:</b> {fmt(r.get('Confidence'))}%</div></div>")
        st.markdown(grid + "</div>", unsafe_allow_html=True)
        st.caption("לניתוח מעמיק של מניה — עבור ללשונית 🔎 ניתוח חברה.")

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
                    b = st.columns([1, 5])
                    if b[0].button("🔍 ניתוח", key=f"an_{k}_{tk}"):
                        analyzed.discard(tk) if tk in analyzed else analyzed.add(tk)
                        st.rerun()
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

elif page == "💎 הזדמנויות":
    st.markdown("### 💎 הזדמנויות — גילוי מרחבי השוק (ציונים · מומנטום · ערך · מובילי סקטור)")
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

elif page == "🚨 התראות":
    st.markdown("### 🚨 מרכז התראות — דוחות · פריצות · זינוקי נפח · חדשות מהותיות")
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

elif page == "📊 אינטליגנציית שוק":
    st.markdown("### 📊 אינטליגנציית שוק — נתונים ועדויות")
    st.caption("כל המספרים נגזרים מנתוני שוק/דוחות וממנועי הניקוד הדטרמיניסטיים — ניתנים לשחזור.")
    sh = load_system_health()
    k = st.columns(4)
    k[0].metric("מניות שנסרקו", sh.get("scanned", "—"))
    k[1].metric("שלמות נתונים", fmt(sh.get("data_completeness"), "%"))
    k[2].metric("אמון ממוצע", fmt(sh.get("avg_trust")))
    k[3].metric("משיכות שנכשלו", sh.get("failed_pulls", "—"))

    st.markdown("#### 📈 טבלת מניות מדורגת")
    cols = ["Ticker", "Name", "ScoreV2", "Score", "ScoreFundamental", "ScoreRisk",
            "TrustScore", "RiskLevel", "ExpectedUpside%", "Confidence", "DailyChange%"]
    view = df[[c for c in cols if c in df.columns]].copy().sort_values("ScoreV2", ascending=False)
    view = view.rename(columns={c: L.get(c, c) for c in view.columns})
    pcfg = {L[c]: st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")
            for c in ("ScoreV2", "Score", "ScoreFundamental", "TrustScore")
            if c in df.columns and L.get(c) in view.columns}
    st.dataframe(view, use_container_width=True, hide_index=True, column_config=pcfg)
    st.caption("ScoreV2 = שקלול פונדמנטלי 35% · טכני 25% · סקטור 20% · חדשות 10% · סיכון 10%.")

    st.markdown("#### 📊 בקטסט — ביצועי אות הפריצה בעבר")
    _, backtest = read_outputs()
    if backtest.empty:
        st.caption("אין נתוני בקטסט.")
    else:
        st.dataframe(backtest, use_container_width=True, hide_index=True)
        st.caption("אחוז הצלחה = שיעור האיתותים שהניבו תשואה חיובית (כולל אימות Out-of-Sample).")

elif page == "⚙️ הגדרות":
    st.markdown("### ⚙️ הגדרות")
    st.markdown(f"<div class='ic-card'><div class='ic-title'>📅 מצב הנתונים</div>"
                f"<div class='ic-sub'>עודכן לאחרונה: <b>{latest}</b></div>"
                f"<div class='ic-sub'>{len(df)} מניות ברשימת המעקב · מקור: Yahoo Finance (חינמי)</div></div>",
                unsafe_allow_html=True)
    if st.button("🔄 רענן נתונים עכשיו", help="מריץ סריקה מחדש (כ‑30–60 שניות). ללא שליחת מייל."):
        with st.spinner("מריץ סריקה מחדש…"):
            try:
                run_scan(); ok = True
            except Exception:
                ok = False
        if ok:
            st.cache_data.clear(); st.success("עודכן!"); st.rerun()
        else:
            st.error("הרענון נכשל.")
    st.markdown("<div class='ic-card'><div class='ic-title'>ℹ️ אודות</div>"
                "<div class='ic-sub'>Stock Agent Pro — פלטפורמת אינטליגנציה השקעתית <b>מבוססת-נתונים בלבד</b>. "
                "<b>ללא AI/LLM וללא המלצות אישיות</b> — כל מסקנה נגזרת מנתוני שוק, דוחות כספיים, מדדים מחושבים "
                "ומנועי ניקוד דטרמיניסטיים, וניתנת לשחזור.</div>"
                "<div class='ic-sub'>המערכת עונה: מה קורה · למה · מה הסיכונים · האם החברה אטרקטיבית · זול/הוגן/יקר.</div>"
                "<div class='ic-sub'>⚠️ מידע בלבד, לא ייעוץ השקעות.</div></div>", unsafe_allow_html=True)

st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")
