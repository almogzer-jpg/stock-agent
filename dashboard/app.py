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
                             SECONDARY, PRIMARY, POSITIVE, WARNING, NEGATIVE, BG, BORDER, ELEV,
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


@st.cache_data(ttl=300, show_spinner=False)
def load_global() -> dict:
    if os.path.exists(config.GLOBAL_JSON):
        with open(config.GLOBAL_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def global_strip_html(g: dict) -> str:
    """Compact green/red market chips from the global artifact."""
    chips = []
    for r in g.get("strip", []):
        p, d1 = r.get("price"), r.get("d1")
        col = MUTED if not isinstance(d1, (int, float)) else (POSITIVE if d1 >= 0 else NEGATIVE)
        pv = "—" if p is None else (f"${p:,.0f}" if r["symbol"].endswith("-USD") else f"{p:,.2f}")
        dv = f"{d1:+.1f}%" if isinstance(d1, (int, float)) else ""
        chips.append(f"<div class='chip'><div class='cl'>{r['name']}</div>"
                     f"<div class='cv'>{pv} <span style='color:{col};font-size:14px'>{dv}</span></div></div>")
    return f"<div class='chiprow'>{''.join(chips)}</div>" if chips else ""


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

# Cross-page navigation request (e.g. "ניתוח חברה" button) — applied BEFORE the
# nav widget is instantiated, since a widget's value can't be set after creation.
if st.session_state.get("_pending_nav"):
    st.session_state["nav"] = st.session_state.pop("_pending_nav")

page = st.sidebar.radio(
    "תצוגה",
    ["🏠 ראשי", "🔎 ניתוח חברה", "💎 הזדמנויות", "🗺️ סקטורים", "🚨 התראות",
     "📊 אינטליגנציית שוק", "⚙️ הגדרות"],
    key="nav",
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

    # ---------- Executive summary — text first (what matters today) ----------
    reg_s, reg_l = regime.get("score"), regime.get("label", "—")
    _top1 = (positive if not positive.empty else df).sort_values("ScoreV2", ascending=False).head(1)
    _secs = sorted(mkt.get("sectors", []), key=lambda s: -s.get("score", 0))
    _crit = [a for a in alerts if a.get("severity") in ("קריטית", "גבוהה")]
    _bits = []
    if len(_top1):
        _r0 = _top1.iloc[0]
        _bits.append(f"ההזדמנות הבולטת: <b style='color:{TEXT}'>{_r0['Ticker']}</b> "
                     f"(ציון {int(_r0['ScoreV2'])}, סיכון {fmt(_r0.get('RiskLevel'))})")
    if _secs:
        _bits.append(f"סקטור מוביל: {_secs[0]['sector']} · חלש: {_secs[-1]['sector']}")
    _bits.append(f"{len(_crit)} התראות קריטיות פתוחות" if _crit else "אין התראות קריטיות")
    st.markdown(
        f"<div style='margin:4px 0 26px'>"
        f"<div style='font-size:26px;font-weight:700;line-height:1.3'>"
        f"השוק במצב {reg_l} <span style='color:{regime_color(reg_s)}'>({fmt(reg_s)}/100)</span>"
        f" · {len(positive)} הזדמנויות פעילות</div>"
        f"<div style='font-size:15px;color:{SECONDARY};margin-top:10px;line-height:1.8'>{' · '.join(_bits)}.</div>"
        f"</div>", unsafe_allow_html=True)

    # ---------- Global market strip (Phase 30) ----------
    _g = load_global()
    if _g.get("strip"):
        st.markdown(global_strip_html(_g), unsafe_allow_html=True)
        st.caption(f"שווקים גלובליים · עודכן {_g.get('updated', '—')} · הרחבה בעמוד אינטליגנציית שוק")

    # ---------- Section 1: Executive KPI strip ----------
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
    ]
    st.markdown(f"<div class='kpi-grid' style='grid-template-columns:repeat(4,1fr)'>{''.join(kpis)}</div>",
                unsafe_allow_html=True)

    # ---------- Section 2: Market Regime + What should I do today ----------
    c = st.columns([1.05, 1.95], gap="large")
    with c[0]:
        st.markdown("#### מצב שוק (Market Regime)")
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
        st.markdown("#### הזדמנויות לבחינה היום")
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
    st.markdown("#### שווקים")
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
    st.markdown("### ההזדמנויות המובילות היום")
    ranked = (positive if not positive.empty else df).sort_values("ScoreV2", ascending=False).head(8)
    from dashboard import views as _VW
    _body = ""
    for i, (_, r) in enumerate(ranked.iterrows(), 1):
        sv = r.get("ScoreV2")
        sv = int(sv) if isinstance(sv, (int, float)) and sv == sv else None
        scol = score_color(sv)
        rb = _VW.risk_badge(r.get("RiskLevel"))
        up = r.get("ExpectedUpside%")
        upc = POSITIVE if isinstance(up, (int, float)) and up >= 0 else NEGATIVE
        chg = r.get("DailyChange%")
        chc = POSITIVE if isinstance(chg, (int, float)) and chg >= 0 else NEGATIVE
        tr = r.get("TrustScore")
        tr = int(tr) if isinstance(tr, (int, float)) and tr == tr else None
        _body += (
            f"<tr>"
            f"<td style='color:{MUTED}'>{i}</td>"
            f"<td><div style='font-weight:700;font-size:16px'>{r['Ticker']}</div>"
            f"<div style='color:{MUTED};font-size:13px'>{r.get('Name', '')}</div></td>"
            f"<td><span class='tbadge' style='color:{PRIMARY}'>"
            f"{market.SECTOR_EN_TO_HE.get(r.get('Sector'), r.get('Sector') or '—')}</span></td>"
            f"<td><b>${fmt(r.get('Price'))}</b><div style='color:{chc};font-size:13px'>"
            f"{f'{chg:+.1f}%' if isinstance(chg, (int, float)) else '—'}</div></td>"
            f"<td><div style='display:flex;align-items:center;gap:10px'>"
            f"<div class='miniprog' style='min-width:84px'><div style='width:{sv or 0}%;background:{scol}'></div></div>"
            f"<b style='color:{scol};font-size:16px'>{sv if sv is not None else chr(8212)}</b></div></td>"
            f"<td><b style='color:{score_color(tr)}'>{tr if tr is not None else chr(8212)}</b></td>"
            f"<td><span class='tbadge' style='color:{rb[3]}'>{rb[0]} {rb[1]}</span></td>"
            f"<td style='color:{upc};font-weight:600'>"
            f"{f'{up:+.1f}%' if isinstance(up, (int, float)) else chr(8212)}</td>"
            f"</tr>")
    _head = "".join(f"<th>{h}</th>" for h in
                    ["#", "חברה", "סקטור", "מחיר", "Score V2", "אמון", "סיכון", "פוטנציאל"])
    st.markdown(f"<table class='sectbl'><thead><tr>{_head}</tr></thead><tbody>{_body}</tbody></table>",
                unsafe_allow_html=True)
    st.caption("ציון V2 = השקלול המלא (פונדמנטלי/טכני/סקטור/חדשות/סיכון) · פוטנציאל = מדד קנייני מחושב.")
    _bc = st.columns(len(ranked) if len(ranked) else 1)
    for j, (_, r) in enumerate(ranked.iterrows()):
        if _bc[j].button(f"🔎 {r['Ticker']}", key=f"hg_{r['Ticker']}", use_container_width=True):
            st.session_state["dd_ticker"] = r["Ticker"]
            st.session_state["_pending_nav"] = "🔎 ניתוח חברה"
            st.rerun()

    # ---------- Sector rotation + upcoming events ----------
    sc2 = st.columns(2)
    _secs_all = sorted(mkt.get("sectors", []), key=lambda s: -s.get("score", 0))
    if _secs_all:
        _sbody = "".join(
            f"<tr><td>{i}</td><td>{s['sector']}</td>"
            f"<td><b style='color:{score_color(s['score'])}'>{s['score']}</b></td>"
            f"<td>{s.get('momentum', '—')}</td>"
            f"<td style='color:{POSITIVE if (s.get('rs') or 0) >= 0 else NEGATIVE}'>{s.get('rs', 0):+.1f}%</td></tr>"
            for i, s in enumerate(_secs_all, 1))
        sc2[0].markdown("#### רוטציית סקטורים")
        sc2[0].markdown(f"<table class='sectbl'><thead><tr><th>#</th><th>סקטור</th><th>ציון</th>"
                        f"<th>מומנטום</th><th>חוזק יחסי</th></tr></thead><tbody>{_sbody}</tbody></table>",
                        unsafe_allow_html=True)
    _upcoming = sorted([(t, e) for t, e in (events or {}).items()
                        if isinstance(e.get("days_to_earnings"), (int, float)) and 0 <= e["days_to_earnings"] <= 45],
                       key=lambda x: x[1]["days_to_earnings"])[:7]
    sc2[1].markdown("#### אירועים קרובים")
    if _upcoming:
        _erows = "".join(
            f"<div style='display:flex;justify-content:space-between;padding:9px 2px;"
            f"border-bottom:1px solid {BORDER};font-size:15px'>"
            f"<span><b>{t}</b> · דוחות כספיים</span>"
            f"<span style='color:{SECONDARY}'>בעוד {int(e['days_to_earnings'])} ימים</span></div>"
            for t, e in _upcoming)
        sc2[1].markdown(f"<div class='ic-card'>{_erows}"
                        f"<div class='ic-sub' style='margin-top:8px'>מקור: תאריכי דוחות של רשימת המעקב (Yahoo).</div></div>",
                        unsafe_allow_html=True)
    else:
        sc2[1].caption("אין אירועים קרובים ידועים ברשימת המעקב.")


# ===========================================================================
# PAGE: AI assistant
# ===========================================================================

elif page == "💎 הזדמנויות":
    st.markdown("### הזדמנויות — מסוף גילוי הזדמנויות")
    uni = load_universe()
    if not uni:
        st.info("הסריקה הרחבה עדיין לא רצה. הרץ במסוף: `python scanner.py ALL` (כ‑1.5 דקות), ואז רענן.")
    else:
        from dashboard import views as VW
        lookup = VW.build_lookup(uni)
        nc = VW.names_cache()

        TIP_SCORE = ("ציון משוקלל 0-100 המשלב פונדמנטל/איכות, תמחור, מומנטום טכני, חוזק סקטור וסיכון. "
                     "80-100 יוצא דופן · 70-79 חזק · 60-69 טוב · 50-59 מעקב · מתחת ל-50 חלש.")
        TIP_VAL = "ציון תמחור: 100 זול מאוד · 70-99 אטרקטיבי · 40-69 הוגן · 0-39 יקר."
        TIP_QUAL = "איכות: צמיחת הכנסות/רווח, רווחיות, ROIC, חוזק מאזן ורמת חוב."
        TIP_MOM = "מומנטום: תשואת המחיר ב-3 חודשים. רוקטה=חזק מאוד, עולה=חיובי, ניטרלי, יורד=שלילי."
        TIP_RISK = "סיכון מחושב מ-Beta, תנודתיות, ירידה מקסימלית וגורמי ריכוז."

        def _i(x):
            return str(int(x)) if isinstance(x, (int, float)) and x == x else "—"

        def _num(x):
            return x if isinstance(x, (int, float)) and x == x else None

        # ---------- Top summary bar (5 premium KPI cards) ----------
        hi = VW.kpi_highlights(uni, mkt)

        def _kc(ico, val, lab, sub, ac, tip):
            return (f"<div class='kpi' style='--ac:{ac}' title='{tip}'><div class='k-ico'>{ico}</div>"
                    f"<div style='font-size:19px;font-weight:800;color:{ac};line-height:1.15'>{val}</div>"
                    f"<div class='k-lab'>{lab}</div><div class='k-sub'>{sub}</div></div>")
        kc = []
        hs, bm, uv, lr, s = (hi["high_score"], hi["best_mom"], hi["undervalued"],
                             hi.get("lowest_risk"), hi["strongest"])
        if hs:
            kc.append(_kc("⭐", hs["Ticker"], "הציון הגבוה ביותר", f"Score V2: {_i(hs.get('ScoreV2'))}",
                          VW.score_band_color(hs.get("ScoreV2")), TIP_SCORE))
        if bm:
            m = bm.get("Ret3m")
            kc.append(_kc("🚀", bm["Ticker"], "מומנטום מוביל",
                          f"{VW.momentum_emoji(m)} {'+' if (m or 0) >= 0 else ''}{_i(m)}% (3ח׳)", PRIMARY,
                          "המניה עם תשואת 3 החודשים הגבוהה ביותר."))
        if uv:
            kc.append(_kc("💎", uv["Ticker"], "המוערכת ביותר בחסר", f"ציון תמחור: {_i(uv.get('Valuation'))}",
                          WARNING, TIP_VAL))
        if lr:
            kc.append(_kc("🛡️", lr["Ticker"], "הסיכון הנמוך ביותר", f"ציון סיכון: {_i(lr.get('RiskScore'))}",
                          POSITIVE, "המניה עם ציון הסיכון הנמוך ביותר (תנודתיות/ביתא/Drawdown)."))
        if s:
            kc.append(_kc("🏆", s["sector_he"], "הסקטור החזק ביותר", f"ציון ממוצע {_i(s['avg_score'])}",
                          "#38bdf8", "הסקטור עם החוזק והציון הממוצע הגבוהים ביותר."))
        st.markdown(f"<div class='kpi-grid' style='grid-template-columns:repeat(5,1fr)'>{''.join(kc)}</div>",
                    unsafe_allow_html=True)

        # ---------- Score V2 explanation ----------
        st.markdown(
            f"<div class='ic-card' style='border-right:5px solid {PRIMARY}'>"
            f"<div class='ic-title'>ℹ️ מהו ציון V2?</div>"
            f"<div class='ic-sub'>ציון משוקלל 0–100 המשלב: פונדמנטל/איכות · תמחור · מומנטום טכני · חוזק סקטור · סיכון.</div>"
            f"<div class='ic-sub' style='margin-top:5px'>"
            f"<span style='color:#22c55e'>80–100 יוצא דופן</span> · "
            f"<span style='color:#38bdf8'>70–79 חזק</span> · "
            f"<span style='color:#facc15'>60–69 טוב</span> · "
            f"<span style='color:#fb923c'>50–59 מעקב</span> · "
            f"<span style='color:#ef4444'>מתחת ל-50 חלש</span></div></div>", unsafe_allow_html=True)

        # ---------- shared helpers ----------
        TAG_SUBSTR = {"פריצה": "פריצה", "מומנטום חזק": "מומנטום חזק", "מוערכת בחסר": "מוערך",
                      "איכות גבוהה": "איכות גבוהה", "תפנית": "תפנית", "רוטציה סקטוריאלית": "רוטציה"}

        def _reason(r):
            bits = []
            m = _num(r.get("Ret3m"))
            if m is not None:
                bits.append("מומנטום חזק מאוד" if m >= 50 else "מומנטום חיובי" if m >= 15
                            else "מומנטום שלילי" if m < 0 else "מומנטום מתון")
            if _num(r.get("SectorScore")) is not None and r["SectorScore"] >= 66:
                bits.append("סקטור מוביל")
            if _num(r.get("ScoreFundamental")) is not None and r["ScoreFundamental"] >= 70:
                bits.append("איכות גבוהה")
            val = _num(r.get("Valuation"))
            if val is not None:
                bits.append("אך התמחור יקר" if val < 40 else "ובתמחור אטרקטיבי" if val >= 65 else "")
            if r.get("RiskLevel") in ("גבוה", "גבוה מאוד"):
                bits.append(f"בסיכון {r['RiskLevel']}")
            bits = [b for b in bits if b]
            return ", ".join(bits) + "." if bits else "ציון משוקלל יציב."

        def _otype(tags):
            return tags[0] if isinstance(tags, list) and tags else "—"

        def _badge(text, color):
            return f"<span class='tbadge' style='color:{color}'>{text}</span>"

        def _go(tk, keyp):
            if st.button("🔎 ניתוח מניה", key=f"{keyp}_{tk}", use_container_width=True):
                st.session_state["dd_ticker"] = tk
                st.session_state["_pending_nav"] = "🔎 ניתוח חברה"
                st.rerun()

        def _full_card(r):
            tk = r["Ticker"]
            nm = VW.company_name(tk, lookup, nc)
            sv = _num(r.get("ScoreV2"))
            scol = VW.score_band_color(sv)
            rb = VW.risk_badge(r.get("RiskLevel"))
            sec_he = market.SECTOR_EN_TO_HE.get(r.get("Sector"), r.get("Sector") or "—")
            mom = _num(r.get("Ret3m"))
            val = _num(r.get("Valuation"))
            qual = _num(r.get("ScoreFundamental"))
            mom_c = POSITIVE if (mom or 0) >= 0 else NEGATIVE
            mom_s = f"{VW.momentum_emoji(mom)} {'+' if (mom or 0) >= 0 else ''}{_i(mom)}%"
            badges = (_badge(sec_he, PRIMARY) + _badge(f"Score V2 {_i(sv)}", scol)
                      + _badge(f"{rb[0]} {rb[1]} / {rb[2]}", rb[3]))
            return (f"<div class='ocard' title='לחץ \"ניתוח מניה\" לדוח מלא' style='border-right:5px solid {scol}'>"
                    f"<div class='oc-head'><div class='oc-av' style='background:{scol}'>{tk[:2]}</div>"
                    f"<div><div class='oc-tk'>{tk}</div><div class='oc-name'>{nm}</div></div></div>"
                    f"<div class='oc-badges'>{badges}</div>"
                    f"<div class='oc-metric'><span>איכות <span class='info' title='{TIP_QUAL}'>?</span></span>"
                    f"<b style='color:{score_color(qual) if qual is not None else MUTED}'>{_i(qual)}</b></div>"
                    f"<div class='oc-metric'><span>תמחור <span class='info' title='{TIP_VAL}'>?</span></span>"
                    f"<b style='color:{score_color(val) if val is not None else MUTED}'>{_i(val)}</b></div>"
                    f"<div class='oc-metric'><span>מומנטום 3ח׳ <span class='info' title='{TIP_MOM}'>?</span></span>"
                    f"<b style='color:{mom_c}'>{mom_s}</b></div>"
                    f"<div class='oc-reason'>{_reason(r)}</div></div>")

        def _panel_item(r):
            tk = r["Ticker"]
            nm = VW.company_name(tk, lookup, nc)
            sv = _num(r.get("ScoreV2"))
            scol = VW.score_band_color(sv)
            rb = VW.risk_badge(r.get("RiskLevel"))
            sec_he = market.SECTOR_EN_TO_HE.get(r.get("Sector"), r.get("Sector") or "—")
            return (f"<div class='pitem' style='--ac:{scol}'>"
                    f"<div class='pi-tk'>{tk}</div><div class='pi-name'>{nm}</div>"
                    f"<div class='oc-badges' style='margin:6px 0'>{_badge(sec_he, PRIMARY)}"
                    f"{_badge('V2 ' + _i(sv), scol)}{_badge(rb[0] + ' ' + rb[1], rb[3])}</div>"
                    f"<div class='oc-reason' style='font-size:12px'>{_reason(r)}</div></div>")

        opps = pd.DataFrame(uni.get("opportunities", []))
        if opps.empty:
            st.caption("אין הזדמנויות מועשרות.")
        else:
            # ---------- Filter bar ----------
            secs = sorted([x for x in opps.get("Sector", pd.Series()).dropna().unique()])
            with st.form("opp_filters", border=True):
                st.markdown("##### סינון הזדמנויות")
                a = st.columns(3)
                sel_sec = a[0].selectbox("סקטור", ["הכל"] + secs, key="f_sec")
                sel_risk = a[1].multiselect("רמת סיכון", ["נמוך", "בינוני", "גבוה", "גבוה מאוד"],
                                            key="f_risk", placeholder="הכל")
                sel_tags = a[2].multiselect("סוג הזדמנות", list(TAG_SUBSTR.keys()),
                                            key="f_tags", placeholder="הכל")
                SCORE_OPTS = {"הכל": 0, "טוב ומעלה (60+)": 60, "חזק ומעלה (70+)": 70, "יוצא דופן (80+)": 80}
                MOM_OPTS = {"הכל": -999, "חיובי (0%+)": 0, "חזק (15%+)": 15, "חזק מאוד (50%+)": 50,
                            "מרשים (100%+)": 100}
                VAL_OPTS = {"הכל": 0, "לא יקר (40+)": 40, "אטרקטיבי (60+)": 60, "זול מאוד (80+)": 80}
                b = st.columns(3)
                min_score = SCORE_OPTS[b[0].selectbox("ציון V2 מינימלי", list(SCORE_OPTS),
                                                      index=1, key="f_score",
                                                      help="ציון משוקלל 0-100: פונדמנטל, טכני, סקטור, חדשות וסיכון.")]
                min_mom = MOM_OPTS[b[1].selectbox("מומנטום מינימלי (3 חודשים)", list(MOM_OPTS),
                                                  index=0, key="f_mom", help="תשואת המחיר ב-3 החודשים האחרונים.")]
                min_val = VAL_OPTS[b[2].selectbox("תמחור מינימלי", list(VAL_OPTS),
                                                  index=0, key="f_val",
                                                  help="ציון תמחור: 100 = זול מאוד · 40-69 הוגן · מתחת ל-40 יקר.")]
                bcols = st.columns([1, 1, 3])
                bcols[0].form_submit_button("✅ החל סינון", type="primary", use_container_width=True)
                reset = bcols[1].form_submit_button("🧹 איפוס סינון", use_container_width=True)
            if reset:
                for kk in ("f_sec", "f_risk", "f_score", "f_mom", "f_val", "f_tags"):
                    st.session_state.pop(kk, None)
                st.rerun()

            v = opps.copy()
            if sel_sec != "הכל":
                v = v[v["Sector"] == sel_sec]
            if sel_risk:
                v = v[v["RiskLevel"].isin(sel_risk)]
            v = v[v["ScoreV2"].fillna(0) >= min_score]
            if "Ret3m" in v:
                v = v[v["Ret3m"].fillna(-999) >= min_mom]
            if "Valuation" in v:
                v = v[v["Valuation"].fillna(0) >= min_val]
            if sel_tags:
                subs = [TAG_SUBSTR[t] for t in sel_tags]
                v = v[v["tags"].apply(lambda ts: isinstance(ts, list)
                                      and any(any(su in t for t in ts) for su in subs))]
            v = v.sort_values("ScoreV2", ascending=False)
            top = st.columns([2, 3])
            top[0].markdown(f"**מציג {len(v)} מניות מתוך {len(opps)}**")
            view = top[1].radio("תצוגה", ["📊 טבלה", "🗂 כרטיסים"], horizontal=True,
                                key="opp_view", label_visibility="collapsed")

            if v.empty:
                st.caption("אין מניות שעוברות את הסינון. נסה להרחיב את התנאים.")
            elif view == "🗂 כרטיסים":
                for cs in range(0, min(len(v), 12), 3):
                    cols = st.columns(3)
                    for j, (_, r) in enumerate(v.iloc[cs:cs + 3].iterrows()):
                        with cols[j]:
                            st.markdown(_full_card(r), unsafe_allow_html=True)
                            _go(r["Ticker"], "gf")
            else:
                # ---------- Professional data grid (default) ----------
                q = st.text_input("🔎 חיפוש (סימול / חברה / סקטור)", key="opp_search").strip().lower()
                vv = v
                if q:
                    def _match(r):
                        nm = VW.company_name(r["Ticker"], lookup, nc)
                        return (q in str(r["Ticker"]).lower() or q in str(nm).lower()
                                or q in str(r.get("Sector", "")).lower())
                    vv = v[v.apply(_match, axis=1)]

                def _val_badge(x):
                    return ("🟢 זול" if x >= 65 else "🟡 הוגן" if x >= 40 else "🔴 יקר") \
                        if isinstance(x, (int, float)) and x == x else "—"

                def _type_badge(tags):
                    t = _otype(tags)
                    for kw, b in [("איכות", "🏆 איכות"), ("מומנטום", "🚀 מומנטום"), ("מוערך", "💎 ערך"),
                                  ("תפנית", "❤️ נסתרת"), ("פריצה", "🚀 פריצה"), ("רוטציה", "🔄 רוטציה")]:
                        if kw in t:
                            return b
                    return t
                def _sr_cell(price_v, dist):
                    if _num(price_v) is None:
                        return "—"
                    d = f" ({'+' if (dist or 0) >= 0 else ''}{dist}%)" if _num(dist) is not None else ""
                    return f"${price_v}{d}"
                rows = []
                for rank, (_, r) in enumerate(vv.iterrows(), 1):
                    rb = VW.risk_badge(r.get("RiskLevel"))
                    rows.append({
                        "דירוג": rank, "סימול": r["Ticker"],
                        "חברה": VW.company_name(r["Ticker"], lookup, nc),
                        "סקטור": market.SECTOR_EN_TO_HE.get(r.get("Sector"), r.get("Sector") or "—"),
                        "Score V2": int(r["ScoreV2"]) if _num(r.get("ScoreV2")) is not None else None,
                        "מומנטום 3ח׳": round(r["Ret3m"], 1) if _num(r.get("Ret3m")) is not None else None,
                        "תמחור": _val_badge(r.get("Valuation")), "סיכון": f"{rb[0]} {rb[1]}",
                        "תמיכה": _sr_cell(r.get("Support"), r.get("DistSupport%")),
                        "התנגדות": _sr_cell(r.get("Resistance"), r.get("DistResistance%")),
                        "סיכון/סיכוי": r.get("RiskReward") if _num(r.get("RiskReward")) is not None else float("nan"),
                        "סוג הזדמנות": _type_badge(r.get("tags")),
                    })
                gdf = pd.DataFrame(rows)
                if gdf.empty:
                    st.caption("אין תוצאות לחיפוש.")
                else:
                    ev = st.dataframe(
                        gdf, use_container_width=True, hide_index=True, height=460,
                        on_select="rerun", selection_mode="single-row", key="opp_grid",
                        column_config={
                            "Score V2": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
                            "מומנטום 3ח׳": st.column_config.NumberColumn(format="%+.1f%%"),
                            "סיכון/סיכוי": st.column_config.NumberColumn(format="%.2f")})
                    cc = st.columns([3, 1])
                    cc[0].caption("מיון: לחיצה על כותרת עמודה · לחיצה על שורה → ניתוח מניה אוטומטי.")
                    cc[1].download_button("📥 ייצוא CSV", gdf.to_csv(index=False).encode("utf-8-sig"),
                                          file_name="opportunities.csv", mime="text/csv", use_container_width=True)
                    if getattr(ev, "selection", None) and ev.selection.get("rows"):
                        st.session_state["dd_ticker"] = gdf.iloc[ev.selection["rows"][0]]["סימול"]
                        st.session_state["_pending_nav"] = "🔎 ניתוח חברה"
                        st.rerun()

        # ---------- Sector heatmap (Finviz-style treemap) ----------
        sec_rows = VW.sector_intel(uni, mkt)
        if sec_rows:
            st.divider()
            st.markdown("#### מפת חום סקטוריאלית")
            st.caption("גודל = מספר הזדמנויות · צבע = Score V2 ממוצע (ירוק חזק · אדום חלש).")
            labels = [f"{r['sector_he']}<br>{_i(r['avg_score'])}" for r in sec_rows]
            fig = go.Figure(go.Treemap(
                labels=labels, parents=[""] * len(sec_rows),
                values=[r["n"] for r in sec_rows],
                marker=dict(colors=[r["avg_score"] if r["avg_score"] is not None else 0 for r in sec_rows],
                            colorscale=[[0, "#ef4444"], [0.4, "#fb923c"], [0.55, "#facc15"],
                                        [0.7, "#22c55e"], [1, "#16a34a"]],
                            cmin=0, cmax=100, line=dict(width=2, color=BG)),
                textinfo="label", textfont=dict(size=15, color="#06121f"),
                hovertemplate="%{label}<br>הזדמנויות: %{value}<extra></extra>"))
            st.plotly_chart(style_fig(fig, 340), use_container_width=True)

            # ---------- Sector intelligence table ----------
            st.markdown("#### טבלת אינטליגנציית סקטורים")
            reco_he = {"Overweight": "הגדלת משקל", "Neutral": "ניטרלי", "Underweight": "הקטנת משקל"}
            reco_col = {"Overweight": POSITIVE, "Neutral": WARNING, "Underweight": NEGATIVE}
            risk_col = {"נמוך": POSITIVE, "בינוני": WARNING, "גבוה": "#fb923c", "גבוה מאוד": NEGATIVE}

            def _bar(val, color, mx=100):
                p = max(0, min(100, (val or 0) / mx * 100))
                return (f"<div class='miniprog'><div style='width:{p:.0f}%;background:{color}'></div></div>")
            head = "".join(f"<th>{h}</th>" for h in
                           ["#", "סקטור", "הזדמנויות", "חברה מובילה", "Score V2 ממוצע", "תמחור ממוצע",
                            "מומנטום 3ח׳", "סיכון ממוצע", "המלצה"])
            body = ""
            for i, r in enumerate(sec_rows, 1):
                acol = score_color(r["avg_score"]) if isinstance(r["avg_score"], (int, float)) else MUTED
                vcol = score_color(r["avg_val"]) if isinstance(r["avg_val"], (int, float)) else MUTED
                m3 = r.get("ret_3m")
                mcol = POSITIVE if isinstance(m3, (int, float)) and m3 >= 0 else NEGATIVE
                ms = (f"{'+' if m3 >= 0 else ''}{m3}%" if isinstance(m3, (int, float)) else "—")
                rk = r.get("avg_risk")
                body += (f"<tr><td>{i}</td>"
                         f"<td><span class='tbadge' style='color:{PRIMARY}'>{r['sector_he']}</span></td>"
                         f"<td><b>{r['n']}</b></td>"
                         f"<td><b>{r['top']}</b></td>"
                         f"<td><div style='display:flex;align-items:center;gap:8px'>{_bar(r['avg_score'], acol)}"
                         f"<b style='color:{acol}'>{_i(r['avg_score'])}</b></div></td>"
                         f"<td><div style='display:flex;align-items:center;gap:8px'>{_bar(r['avg_val'], vcol)}"
                         f"<b style='color:{vcol}'>{_i(r['avg_val'])}</b></div></td>"
                         f"<td><span style='color:{mcol}'>{ms}</span></td>"
                         f"<td><span style='color:{risk_col.get(rk, MUTED)}'>{rk or '—'}</span></td>"
                         f"<td><span class='tbadge' style='color:{reco_col[r['reco']]}'>{reco_he[r['reco']]}</span></td></tr>")
            st.markdown(f"<table class='sectbl'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>",
                        unsafe_allow_html=True)
            st.caption("המלצה נגזרת מחוזק הסקטור (Overweight ≥66 · Underweight <40) — דטרמיניסטי.")
elif page == "🗺️ סקטורים":
    st.markdown("### אינטליגנציית סקטורים")
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
    st.markdown("### מרכז התראות — דוחות · פריצות · זינוקי נפח · חדשות מהותיות")
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
        # Grouped by severity (action center): each alert → open the analysis.
        _sev_hdr = [("גבוהה", "🔴 קריטיות — דורשות התייחסות", NEGATIVE),
                    ("בינונית", "🟠 חשובות", "#fb923c"),
                    ("מידע", "🔵 מידע", PRIMARY)]
        import re as _re
        for sev_key, sev_title, col in _sev_hdr:
            group = [a for a in center if a.get("severity") == sev_key]
            if not group:
                continue
            st.markdown(f"#### {sev_title} <span style='color:{MUTED};font-size:15px'>({len(group)})</span>",
                        unsafe_allow_html=True)
            for i, a in enumerate(group):
                tk = a.get("scope")
                valid_tk = isinstance(tk, str) and _re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,5}", tk)
                cc = st.columns([6, 1])
                cc[0].markdown(
                    f"<div class='card' style='border-right:3px solid {col};padding:14px 18px;margin-bottom:8px'>"
                    f"<span style='font-weight:600'>{type_icon.get(a['type'], '🔔')} {a['type']}</span>"
                    f"<span style='color:{MUTED}'> · {a.get('scope', '')}</span><br>"
                    f"<span style='color:{SECONDARY}'>{a['message']}</span></div>",
                    unsafe_allow_html=True)
                if valid_tk and cc[1].button(f"🔎 {tk}", key=f"alw_{sev_key}_{i}_{tk}",
                                             use_container_width=True):
                    st.session_state["dd_ticker"] = tk
                    st.session_state["_pending_nav"] = "🔎 ניתוח חברה"
                    st.rerun()

elif page == "🔎 ניתוח חברה":
    import deepdive
    from deepdive_report import to_html
    from indicators.technical import rsi as _rsi

    st.markdown("### ניתוח חברה — Company Deep Dive")
    st.caption("הזן סימול מניה לקבלת ניתוח השקעה מלא. נתונים חיים מ-Yahoo Finance · " + deepdive.DISCLAIMER)
    q = st.columns([2, 1, 4])
    st.session_state.setdefault("dd_ticker", "AAPL")
    tkin = q[0].text_input("סימול", key="dd_ticker", label_visibility="collapsed",
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
            mkt_close = bundle.get("mkt_close")

            # ---- Research-report header (decision data first) ----
            v2 = sc["final_v2"]["value"]
            chg = _num_or(md["daily_change"])
            chg_c = POSITIVE if (chg or 0) >= 0 else NEGATIVE
            scen_by = {s["key"]: s for s in rep.get("scenarios", [])}
            base_t = (scen_by.get("base") or {}).get("target", {})
            up = base_t.get("upside")
            up_txt = f"{'+' if up >= 0 else ''}{up}%" if isinstance(up, (int, float)) else "—"
            up_c = (POSITIVE if up >= 0 else NEGATIVE) if isinstance(up, (int, float)) else MUTED
            qual = sc["fundamental"]["value"]
            risk_c = (NEGATIVE if (rk["risk_score"] or 0) >= 66
                      else WARNING if (rk["risk_score"] or 0) >= 33 else POSITIVE)
            reco_he_txt = op["recommendation"].split("·")[-1].strip() if isinstance(op.get("recommendation"), str) else "—"

            def _hm(lbl, val, color=TEXT):
                return (f"<div style='min-width:104px'><div style='color:{MUTED};font-size:13px'>{lbl}</div>"
                        f"<div style='font-size:19px;font-weight:600;color:{color};margin-top:3px'>{val}</div></div>")
            reco_pill = (f"<span class='tbadge' style='color:{PRIMARY};font-size:15px;padding:7px 18px'>"
                         f"{'🟢' if 'Buy' in str(reco_he_txt) or 'קנייה' in reco_he_txt else '🟡' if reco_he_txt in ('מעקב', 'החזקה') else '🔴'} "
                         f"{reco_he_txt}</span>")
            st.markdown(
                f"<div class='ic-card' style='padding:28px 30px'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:20px;flex-wrap:wrap'>"
                f"<div style='display:flex;gap:14px;align-items:center'>"
                f"<div style='width:52px;height:52px;border-radius:14px;background:{ELEV};display:flex;"
                f"align-items:center;justify-content:center;font-weight:700;font-size:17px;color:{PRIMARY};flex:none'>{tkin[:2]}</div>"
                f"<div><div style='font-size:26px;font-weight:700;line-height:1.2'>{o['name']}</div>"
                f"<div style='color:{MUTED};font-size:15px;margin-top:3px'>{tkin} · {o['sector_he']} · {o['industry']} · {md['market_cap']}</div>"
                f"<div style='margin-top:10px'>{reco_pill}</div></div></div>"
                f"<div style='text-align:left'>"
                f"<div style='font-size:40px;font-weight:700;line-height:1.02;letter-spacing:-1.2px'>{md['price']}</div>"
                f"<div style='color:{chg_c};font-size:18px;font-weight:600;margin-top:3px'>{md['daily_change']}</div>"
                f"<div style='color:{MUTED};font-size:14px'>היום</div></div></div>"
                f"<div style='display:flex;gap:32px;flex-wrap:wrap;margin-top:22px;border-top:1px solid {BORDER};padding-top:18px'>"
                + _hm("מחיר יעד (קונצנזוס)", base_t.get("price", "—"))
                + _hm("אפסייד", up_txt, up_c)
                + _hm("סיכון", rk["category"], risk_c)
                + _hm("איכות", int(qual) if isinstance(qual, (int, float)) else "—",
                      score_color(qual if isinstance(qual, (int, float)) else None))
                + _hm("ציון v2", v2, score_color(v2))
                + _hm("אמון", sc["trust"]["value"], score_color(sc["trust"]["value"]))
                + "</div></div>", unsafe_allow_html=True)

            # ==== Investment Decision (Phase 25) — the signature section ====
            _dec_fn = getattr(deepdive, "investment_decision", None)
            dec = _dec_fn(rep, regime_score=(mkt.get("regime") or {}).get("score")) if _dec_fn else None
            if dec:
                st.markdown("#### החלטת השקעה")
                NEA = "אין מספיק נתונים"

                def _n2(v, suf="", plus=False):
                    if not isinstance(v, (int, float)):
                        return "—"
                    s = f"{v:+.1f}" if plus else f"{v:,.1f}".rstrip("0").rstrip(".")
                    return f"{s}{suf}"
                reco = dec["recommendation"]
                reco_he = reco.split("·")[-1].strip() if isinstance(reco, str) else NEA
                reco_c = (POSITIVE if any(k in reco for k in ("Buy",)) else
                          NEGATIVE if any(k in reco for k in ("Avoid", "Reduce")) else WARNING)
                conf = dec.get("confidence")
                ent = dec["entry"]
                ent_c = {"excellent": POSITIVE, "good": POSITIVE, "wait": WARNING,
                         "extended": "#fb923c", "avoid": NEGATIVE}.get(ent["band"], MUTED)
                rr_c = {"מצוין": POSITIVE, "טוב": POSITIVE, "סביר": WARNING, "חלש": NEGATIVE}.get(dec.get("rr_interpretation"), MUTED)

                def _kv(lbl, val, color=TEXT, sub=""):
                    return (f"<div style='min-width:96px'><div style='color:{MUTED};font-size:12.5px'>{lbl}</div>"
                            f"<div style='font-size:18px;font-weight:700;color:{color}'>{val}</div>"
                            + (f"<div style='color:{MUTED};font-size:11.5px'>{sub}</div>" if sub else "") + "</div>")
                c3 = st.columns([1.15, 1.5, 1])
                c3[0].markdown(
                    f"<div class='ic-card' style='height:100%;background:{ELEV}'>"
                    f"<div style='color:{MUTED};font-size:12.5px'>המלצה</div>"
                    f"<div style='font-size:30px;font-weight:700;color:{reco_c};line-height:1.15'>{reco_he}</div>"
                    f"<div style='margin-top:10px;color:{MUTED};font-size:12.5px'>ביטחון (ציון אמון)</div>"
                    f"<div class='sbar-t' style='margin-top:4px'><div class='sbar-f' style='width:{conf if isinstance(conf,(int,float)) else 0}%;background:{score_color(conf)}'></div></div>"
                    f"<div style='font-size:14px;font-weight:600;color:{score_color(conf)}'>{int(conf) if isinstance(conf,(int,float)) else NEA}%</div>"
                    f"<div style='margin-top:10px;color:{MUTED};font-size:12.5px'>אופק השקעה</div>"
                    f"<div style='font-size:15px;font-weight:600'>{dec['horizon']}</div>"
                    f"<div style='margin-top:10px;color:{MUTED};font-size:12.5px'>איכות כניסה</div>"
                    f"<div style='font-size:16px;font-weight:700;color:{ent_c}'>{ent['emoji']} {ent['label']}</div>"
                    f"<div style='color:{SECONDARY};font-size:12.5px;line-height:1.6;margin-top:4px'>"
                    + " · ".join(ent["reasons"][:3]) + "</div></div>", unsafe_allow_html=True)
                c3[1].markdown(
                    f"<div class='ic-card' style='height:100%'>"
                    f"<div style='display:flex;gap:22px;flex-wrap:wrap'>"
                    + _kv("מחיר נוכחי", f"${_n2(dec.get('price'))}")
                    + _kv("מחיר יעד", dec.get("target", "—"), PRIMARY, "קונצנזוס אנליסטים")
                    + _kv("שווי הוגן", dec.get("fair_value", "—"), TEXT, "קונצנזוס")
                    + _kv("שולי ביטחון", _n2(dec.get("margin_of_safety"), "%", plus=True),
                          POSITIVE if (dec.get("margin_of_safety") or 0) > 0 else NEGATIVE)
                    + _kv("תמיכה", f"${_n2(dec.get('support'))}" if dec.get("support") else "—", POSITIVE)
                    + _kv("התנגדות", f"${_n2(dec.get('resistance'))}" if dec.get("resistance") else "—", NEGATIVE)
                    + _kv("סיכון", dec.get("risk_level"), TEXT)
                    + _kv("ציון V2", dec.get("score_v2") if dec.get("score_v2") is not None else "—",
                          score_color(dec.get("score_v2")))
                    + "</div>"
                    + (lambda z: ("" if not z else
                        f"<div style='margin-top:16px;color:{MUTED};font-size:12.5px'>טווח רמות</div>"
                        f"<div style='direction:ltr;position:relative;height:44px;margin-top:6px'>"
                        f"<div style='position:absolute;top:18px;left:0;right:0;height:8px;border-radius:5px;"
                        f"background:linear-gradient(90deg,{POSITIVE}55,{WARNING}44,{NEGATIVE}55)'></div>"
                        + "".join(
                            f"<div style='position:absolute;left:{p}%;top:{tp}px;transform:translateX(-50%);text-align:center'>"
                            f"<div style='width:2px;height:14px;background:{cc};margin:0 auto'></div>"
                            f"<div style='font-size:10.5px;color:{cc};white-space:nowrap'>{lb}</div></div>"
                            for p, lb, cc, tp in [
                                (z.get("pos_support"), f"תמיכה ${_n2(z.get('support'))}", POSITIVE, 26),
                                (z.get("pos_resistance"), f"התנגדות ${_n2(z.get('resistance'))}", NEGATIVE, 26),
                                (z.get("pos_price"), f"מחיר ${_n2(z.get('price'))}", TEXT, 0),
                                (z.get("pos_fair"), f"יעד ${_n2(z.get('fair'))}", PRIMARY, 0),
                            ] if isinstance(p, (int, float))) + "</div>"))(dec.get("zones"))
                    + "</div>", unsafe_allow_html=True)
                c3[2].markdown(
                    f"<div class='ic-card' style='height:100%'>"
                    f"<div style='color:{MUTED};font-size:12.5px'>אפסייד צפוי (ליעד)</div>"
                    f"<div style='font-size:26px;font-weight:700;color:{POSITIVE if (dec.get('upside') or 0)>=0 else NEGATIVE}'>{_n2(dec.get('upside'), '%', plus=True)}</div>"
                    f"<div style='color:{MUTED};font-size:12.5px;margin-top:8px'>דאונסייד (לתמיכה)</div>"
                    f"<div style='font-size:26px;font-weight:700;color:{NEGATIVE}'>{_n2(dec.get('downside'), '%', plus=True)}</div>"
                    f"<div style='color:{MUTED};font-size:12.5px;margin-top:8px'>יחס סיכון/סיכוי</div>"
                    f"<div style='font-size:26px;font-weight:700;color:{rr_c}'>{dec.get('rr') if dec.get('rr') is not None else '—'}"
                    f" <span style='font-size:14px'>{dec.get('rr_interpretation') or ''}</span></div>"
                    f"<div style='color:{MUTED};font-size:12.5px;margin-top:8px'>מתאים ל</div>"
                    f"<div>" + " ".join(f"<span class='tbadge' style='color:{PRIMARY};margin:2px'>{t}</span>"
                                        for t in dec.get("investor_types", [])) + "</div></div>",
                    unsafe_allow_html=True)

                # Checklist + decision matrix
                ch_c = {"good": POSITIVE, "neutral": WARNING, "weak": NEGATIVE, "na": MUTED}
                ch_i = {"good": "🟢", "neutral": "🟡", "weak": "🔴", "na": "⚪"}
                chips = "".join(
                    f"<span class='tbadge' style='color:{ch_c[stt]};margin:3px' "
                    f"title='{name}: {(str(val) + sfx) if isinstance(val, (int, float)) else (val or NEA)}'>"
                    f"{ch_i[stt]} {name}</span>"
                    for name, val, stt, sfx in dec.get("checklist", []))
                mx = dec.get("matrix", {})
                mbars = "".join(
                    f"<div style='display:flex;align-items:center;gap:8px;margin:4px 0'>"
                    f"<span style='min-width:110px;color:{SECONDARY};font-size:13px'>{k}</span>"
                    f"<div class='miniprog' style='flex:1'><div style='width:{v if isinstance(v,(int,float)) else 0}%;background:{score_color(v)}'></div></div>"
                    f"<b style='color:{score_color(v)};min-width:44px;text-align:left'>{(str(round(v/10,1)) + '/10') if isinstance(v,(int,float)) else '—'}</b></div>"
                    for k, v in mx.items())
                m2 = st.columns(2)
                m2[0].markdown(f"<div class='ic-card' style='height:100%'><div class='ic-title'>צ׳ק-ליסט מוסדי</div>"
                               f"<div style='margin-top:8px'>{chips}</div>"
                               f"<div class='ic-sub' style='margin-top:8px;font-size:12.5px'>ריחוף על פריט מציג את הערך. ⚪ = {NEA}.</div></div>",
                               unsafe_allow_html=True)
                m2[1].markdown(f"<div class='ic-card' style='height:100%'><div class='ic-title'>מטריצת החלטה</div>"
                               f"<div style='margin-top:8px'>{mbars}"
                               f"<div style='display:flex;justify-content:space-between;margin-top:8px;border-top:1px solid {BORDER};padding-top:8px'>"
                               f"<b>סה\"כ</b><b style='color:{score_color(dec.get('score_v2'))};font-size:18px'>{dec.get('score_v2') if dec.get('score_v2') is not None else '—'} / 100</b></div></div></div>",
                               unsafe_allow_html=True)

                w2 = st.columns(2)
                w2[0].markdown(f"<div class='ic-card' style='height:100%'><div class='ic-title'>מה צריך לקרות כדי שההשקעה תשתפר?</div>"
                               + "".join(f"<div class='ic-sub' style='margin:4px 0'>• {x}</div>" for x in dec.get("wait_for", []))
                               + "</div>", unsafe_allow_html=True)
                w2[1].markdown(f"<div class='ic-card' style='height:100%'><div class='ic-title'>מה עלול להשתבש?</div>"
                               + ("".join(f"<div class='ic-sub' style='margin:4px 0'>• {x}</div>" for x in dec.get("risks", []))
                                  or f"<div class='ic-sub'>{NEA}</div>") + "</div>", unsafe_allow_html=True)
                st.caption("כל הערכים נגזרים מהמדדים המחושבים במערכת — הנתונים מצביעים, לא תחזית. "
                           "מחיר יעד/שווי הוגן = קונצנזוס אנליסטים. מידע בלבד, לא ייעוץ השקעות.")

            # ---- Performance section (Phase 20) ----
            import technicals as _tech
            st.markdown("#### ביצועי מחיר")
            rets = [("שבוע", md["ret_1w"]), ("חודש", md["ret_1m"]), ("3 ח'", md["ret_3m"]),
                    ("6 ח'", md["ret_6m"]), ("YTD", md["ytd"]), ("שנה", md["ret_1y"]), ("3 שנים", md["ret_3y"])]

            def _pchip(lbl, vstr):
                val = _num_or(vstr)
                if val is None:
                    return (f"<div class='chip'><div class='cl'>{lbl}</div>"
                            f"<div class='cv' style='color:{MUTED}'>—</div></div>")
                col = POSITIVE if val > 0.5 else NEGATIVE if val < -0.5 else MUTED
                return (f"<div class='chip'><div class='cl'>{lbl}</div>"
                        f"<div class='cv' style='color:{col}'>{vstr}</div></div>")
            st.markdown(f"<div class='chiprow'>{''.join(_pchip(l, v) for l, v in rets)}</div>",
                        unsafe_allow_html=True)

            periods = ["1W", "1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "MAX", "מותאם"]
            sel = st.radio("תקופה", periods, index=5, horizontal=True, key="perf_period")
            cstart = cend = None
            per = "CUSTOM" if sel == "מותאם" else sel
            cl = hist["Close"].dropna()
            if sel == "מותאם" and len(cl):
                dc = st.columns(2)
                cstart = dc[0].date_input("📅 מתאריך", value=(cl.index[-1] - pd.Timedelta(days=365)).date(), key="perf_start")
                cend = dc[1].date_input("📅 עד תאריך", value=cl.index[-1].date(), key="perf_end")
            perf = None
            _perf_fn = getattr(_tech, "performance", None)
            if hist is not None and _perf_fn is not None:
                try:
                    perf = _perf_fn(hist["Close"], mkt_close, period=per, start=cstart, end=cend)
                except Exception:
                    perf = None
            if perf is None:
                st.caption("נתוני ביצועים אינם זמינים כרגע (נסה לרענן).")

            if perf:
                sret, bret, alpha = perf["stock"], perf["bench"], perf["alpha"]
                scol = POSITIVE if sret >= 0 else NEGATIVE
                lab = {"1W": "שבוע", "1M": "חודש", "3M": "3 חודשים", "6M": "6 חודשים", "YTD": "מתחילת השנה",
                       "1Y": "שנה", "3Y": "3 שנים", "5Y": "5 שנים", "MAX": "מקסימום", "מותאם": "טווח מותאם"}.get(sel, sel)
                mx = max(abs(sret), abs(bret or 0), abs(alpha or 0)) or 1

                def _cbar(name, val, color):
                    if val is None:
                        return f"<div class='cmp'><div class='cl'><span>{name}</span><b>—</b></div></div>"
                    c2 = POSITIVE if val >= 0 else NEGATIVE
                    return (f"<div class='cmp'><div class='cl'><span>{name}</span>"
                            f"<b style='color:{c2}'>{val:+.2f}%</b></div>"
                            f"<div class='cmptrack'><div class='cmpfill' style='width:{abs(val)/mx*100:.0f}%;background:{color}'></div></div></div>")
                st.markdown(
                    f"<div class='ic-card'><div class='ic-sub'>תשואת המניה · {lab}</div>"
                    f"<div style='font-size:34px;font-weight:800;color:{scol};line-height:1.1'>{sret:+.2f}%</div>"
                    + _cbar("המניה", sret, PRIMARY) + _cbar("S&P 500", bret, SECONDARY)
                    + _cbar("Alpha (עודף תשואה)", alpha, POSITIVE if (alpha or 0) >= 0 else NEGATIVE)
                    + "</div>", unsafe_allow_html=True)

                if alpha is not None:
                    ins_p = (f"🟢 המניה היכתה את S&P 500 ב-{alpha:+.1f}% בתקופה זו." if alpha >= 2
                             else f"🔴 המניה פיגרה אחרי הבנצ'מרק ({alpha:+.1f}%)." if alpha <= -2
                             else f"🟡 ביצוע דומה ל-S&P 500 ({alpha:+.1f}%).")
                else:
                    ins_p = "🟢 תשואה חיובית בתקופה." if sret >= 0 else "🔴 תשואה שלילית בתקופה."
                st.markdown(f"<div class='ic-sub' style='margin:2px 0 8px'>{ins_p}</div>", unsafe_allow_html=True)

                def _mc(lbl2, val, suf=""):
                    return (f"<div class='pcard' style='--ac:{PRIMARY}'><div class='pl'>{lbl2}</div>"
                            f"<div class='pv' style='color:{TEXT}'>{(str(val) + suf) if val is not None else '—'}</div></div>")
                st.markdown("<div class='perf-grid' style='grid-template-columns:repeat(4,1fr)'>"
                            + _mc("CAGR", perf["cagr"], "%") + _mc("תנודתיות", perf["vol"], "%")
                            + _mc("ירידה מקס׳", perf["maxdd"], "%") + _mc("Sharpe", perf["sharpe"])
                            + "</div>", unsafe_allow_html=True)
                st.caption("CAGR/תנודתיות/Sharpe/ירידה מקסימלית — מחושבים לתקופה הנבחרת. לצרכי מידע בלבד.")

            # ---- Price chart with MAs + support/resistance (date x-axis) ----
            def _date_axis(fig_):
                """Real dates on the x-axis (DD/MM), weekends hidden (no gaps)."""
                fig_.update_xaxes(tickformat="%d/%m/%y", hoverformat="%d/%m/%Y",
                                  rangebreaks=[dict(bounds=["sat", "mon"])])
                return fig_

            if hist is not None and "Close" in hist.columns:
                c = hist["Close"].dropna()
                if perf is not None:
                    c = c[(c.index >= perf["start"]) & (c.index <= perf["end"])]
                else:
                    c = c.tail(252)
                fig = go.Figure()
                fig.add_trace(go.Scatter(y=c.values, x=c.index, name="מחיר", line_color=PRIMARY))
                for n, col in [(20, "#FFC107"), (50, "#B388FF"), (200, "#E6EDF7")]:
                    if len(c) >= n:
                        fig.add_trace(go.Scatter(y=c.rolling(n).mean().values, x=c.index,
                                                 name=f"MA{n}", line=dict(width=1.3, color=col)))
                sr = tech["support_resistance"]
                if sr.get("support"):
                    fig.add_hline(y=sr["support"], line_dash="dot", line_color=POSITIVE,
                                  annotation_text=f"תמיכה {sr['support']}")
                if sr.get("resistance"):
                    fig.add_hline(y=sr["resistance"], line_dash="dot", line_color=NEGATIVE,
                                  annotation_text=f"התנגדות {sr['resistance']}")
                fig.update_layout(title=f"{tkin} · מחיר + ממוצעים נעים ({sel})")
                st.plotly_chart(_date_axis(style_fig(fig, 320)), use_container_width=True)

                # Volume / RSI / MACD — collapsed, rendered only on demand (lazy)
                with st.expander("אינדיקטורים · נפח / RSI / MACD"):
                    if st.toggle("הצג אינדיקטורים", key="dd_ind"):
                        ch = st.columns(3)
                        vv = hist["Volume"].dropna().tail(120)
                        fv = go.Figure(go.Bar(y=vv.values, x=vv.index, marker_color="#26A69A"))
                        fv.update_layout(title="נפח מסחר (120 ימים)")
                        ch[0].plotly_chart(_date_axis(style_fig(fv, 220)), use_container_width=True)

                        rsis = _rsi(c, 14).dropna().tail(180)
                        fr = go.Figure(go.Scatter(y=rsis.values, x=rsis.index, line_color="#00C2FF"))
                        fr.add_hline(y=70, line_dash="dot", line_color=NEGATIVE)
                        fr.add_hline(y=30, line_dash="dot", line_color=POSITIVE)
                        fr.update_layout(title="RSI(14)", yaxis_range=[0, 100])
                        ch[1].plotly_chart(_date_axis(style_fig(fr, 220)), use_container_width=True)

                        mser = tech["macd"].get("_series")
                        if mser:
                            ml, sg, hh = mser["macd"].tail(180), mser["signal"].tail(180), mser["hist"].tail(180)
                            fm = go.Figure()
                            fm.add_trace(go.Bar(y=hh.values, x=hh.index, name="היסטוגרמה",
                                                marker_color=[POSITIVE if v >= 0 else NEGATIVE for v in hh.values]))
                            fm.add_trace(go.Scatter(y=ml.values, x=ml.index, name="MACD", line_color=PRIMARY))
                            fm.add_trace(go.Scatter(y=sg.values, x=sg.index, name="Signal", line_color=WARNING))
                            fm.update_layout(title="MACD")
                            ch[2].plotly_chart(_date_axis(style_fig(fm, 220)), use_container_width=True)

            # ---- Executive summary (text first: should I investigate, why, risks) ----
            st.markdown("#### תקציר מנהלים")
            pros3 = [x for x in pc["pros"] if x != "—"][:3]
            cons3 = [x for x in pc["cons"] if x != "—"][:3]
            _desc = o.get("summary_he") or o.get("he_line") or ""
            _desc = (_desc[:300] + "…") if isinstance(_desc, str) and len(_desc) > 300 else _desc
            st.markdown(
                f"<div class='ic-card' style='padding:24px 26px'>"
                f"<div style='font-size:15px;color:{TEXT};line-height:1.8;font-weight:600'>{op['attractive']}</div>"
                f"<div style='font-size:15px;color:{SECONDARY};line-height:1.8;margin-top:10px'>{_desc}</div>"
                f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:26px;margin-top:18px'>"
                f"<div><div style='color:{POSITIVE};font-weight:600;margin-bottom:6px'>חוזקות מרכזיות</div>"
                + ("".join(f"<div style='color:{SECONDARY};margin:4px 0'>• {x}</div>" for x in pros3) or "—")
                + f"</div><div><div style='color:{NEGATIVE};font-weight:600;margin-bottom:6px'>סיכונים מרכזיים</div>"
                + ("".join(f"<div style='color:{SECONDARY};margin:4px 0'>• {x}</div>" for x in cons3) or "—")
                + "</div></div></div>", unsafe_allow_html=True)
            if isinstance(o["summary"], str) and o["summary"] != NA_:
                with st.expander("תיאור מלא (אנגלית)"):
                    st.write(o["summary"])

            # ---- Financials + Valuation tables ----
            def _tbl(rows):
                return "<table style='width:100%;border-collapse:collapse'>" + "".join(
                    f"<tr><td style='color:{MUTED};padding:7px 8px;border-bottom:1px solid {BORDER};font-size:14.5px'>{k}</td>"
                    f"<td style='text-align:left;padding:7px 8px;border-bottom:1px solid {BORDER};font-weight:600;font-size:14.5px'>{v}</td></tr>"
                    for k, v in rows) + "</table>"
            fcol = st.columns(2)
            fcol[0].markdown("#### דוחות כספיים")
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
            fcol[1].markdown("#### תמחור")
            vcolor = score_color(val["score"])
            fcol[1].markdown(f"<div class='ic-card'>" + _tbl([
                ("מכפיל עתידי", val["forward_pe"]), ("מכפיל נוכחי", val["trailing_pe"]),
                ("PEG", val["peg"]), ("מחיר/מכירות", val["price_sales"]),
                ("EV/EBITDA", val["ev_ebitda"]), ("מחיר/FCF", val["price_fcf"]),
            ]) + f"<div style='margin-top:10px;font-weight:800;color:{vcolor}'>{val['label']}</div></div>",
                unsafe_allow_html=True)

            # ---- Score breakdown ----
            st.markdown("#### ציוני Stock Agent")
            rh = sc["risk"]["value"]
            bars = (score_bar("ציון V2", v2) + score_bar("טכני", sc["technical"]["value"])
                    + score_bar("פונדמנטלי", _num_or(sc["fundamental"]["value"]))
                    + score_bar("סקטור", _num_or(sc["sector"]["value"]))
                    + score_bar("חדשות", _num_or(sc["news"]["value"]))
                    + score_bar("ניהול סיכון", (None if not isinstance(rh, (int, float)) else 100 - rh))
                    + score_bar("אמון", sc["trust"]["value"]))
            st.markdown(f"<div class='ic-card'>{bars}<div class='ic-sub' style='margin-top:8px'>{sc['final_v2']['explain']}</div></div>",
                        unsafe_allow_html=True)

            # ---- Technical analysis ----
            st.markdown("#### ניתוח טכני")
            ma = tech["moving_averages"]
            tsub = tech["sub_scores"]
            tc = st.columns([1.3, 1])
            _rsiv = tech["rsi"] if isinstance(tech["rsi"], (int, float)) else None
            _mh = (tech.get("macd") or {}).get("hist")
            _mrise = (tech.get("macd") or {}).get("rising")
            _vr = (tech.get("volume") or {}).get("ratio")
            _above = [n for n in (50, 200) if ma.get(f"ma{n}") and ma.get("price") and ma["price"] > ma[f"ma{n}"]]
            _trows = [
                ("מגמה", tech["trend"], "כיוון המחיר מול הממוצעים",
                 "🟢" if "עלייה" in str(tech["trend"]) else "🔴" if "ירידה" in str(tech["trend"]) else "🟡"),
                ("מומנטום", tech["momentum"], "עוצמת התנועה האחרונה",
                 {"חזק": "🟢", "חלש": "🔴"}.get(tech["momentum"], "🟡")),
                ("RSI", tech["rsi"],
                 "קנוי-יתר" if (_rsiv or 50) >= 75 else "מכור-יתר" if (_rsiv or 50) <= 30 else "טווח בריא",
                 "🔴" if _rsiv is not None and (_rsiv >= 75 or _rsiv <= 30) else
                 "🟢" if _rsiv is not None and 50 <= _rsiv < 75 else "🟡"),
                ("MACD", _disp(_mh), "חיובי ומתחזק" if (_mh or 0) > 0 and _mrise else
                 "חיובי" if (_mh or 0) > 0 else "שלילי",
                 "🟢" if (_mh or 0) > 0 and _mrise else "🟡" if (_mh or 0) > 0 else "🔴"),
                ("ממוצעים נעים", f"MA50 {_disp(ma.get('ma50'))} · MA200 {_disp(ma.get('ma200'))}",
                 "מעל 50 ו-200" if len(_above) == 2 else "מעל חלק מהממוצעים" if _above else "מתחת לממוצעים",
                 "🟢" if len(_above) == 2 else "🟡" if _above else "🔴"),
                ("ATR", _disp(tech["atr"]), "טווח תנועה יומי ממוצע", "🟡"),
                ("נפח", _disp(_vr, ) if _vr is None else f"פי {_vr}", "מול ממוצע 20 יום",
                 "🟢" if (_vr or 0) >= 1.5 else "🟡" if (_vr or 0) >= 0.8 else "🔴"),
                ("מרחק משיא", f"{_disp(tech['high_low'].get('dist_from_high'))}%", "מהשיא של 52 שבועות",
                 "🟢" if (tech['high_low'].get('dist_from_high') or 99) <= 5 else "🟡"),
            ]
            _trows_html = "".join(
                f"<div style='display:flex;align-items:center;gap:12px;padding:9px 2px;border-bottom:1px solid {BORDER}'>"
                f"<span style='flex:0 0 20px'>{light}</span>"
                f"<span style='flex:1;color:{SECONDARY}'>{nm_}</span>"
                f"<b style='flex:0 0 auto'>{val_}</b>"
                f"<span style='flex:0 0 34%;color:{MUTED};font-size:14px;text-align:left'>{mean_}</span></div>"
                for nm_, val_, mean_, light in _trows)
            tc[0].markdown(f"<div class='ic-card'>{_trows_html}"
                           f"<div class='ic-sub' style='margin-top:10px'>{tech['opinion']}</div></div>",
                           unsafe_allow_html=True)
            tc[1].markdown("<div class='ic-card'>" + score_bar("מגמה", tsub["trend"]) + score_bar("מומנטום", tsub["momentum"])
                           + score_bar("נפח", tsub["volume"]) + score_bar("תנודתיות (רגוע=גבוה)", tsub["volatility"]) + "</div>",
                           unsafe_allow_html=True)

            # ---- Support & Resistance levels (Phase 24) ----
            srl = tech.get("sr_levels")
            st.markdown("#### רמות תמיכה והתנגדות")
            if not srl:
                st.caption(NA_)
            else:
                def _lvl(lbl, price_v, dist, color):
                    pv = f"${price_v}" if price_v is not None else "—"
                    dv = (f"{'+' if (dist or 0) >= 0 else ''}{dist}%" if dist is not None else "")
                    return (f"<div style='min-width:150px'><div style='color:{MUTED};font-size:12.5px'>{lbl}</div>"
                            f"<div style='font-size:22px;font-weight:700;color:{color}'>{pv}</div>"
                            f"<div style='color:{color};font-size:13px'>{dv}</div></div>")
                rr, rrl = srl.get("risk_reward"), srl.get("risk_reward_label")
                rr_c = POSITIVE if rrl == "אטרקטיבי" else (NEGATIVE if rrl == "לא אטרקטיבי" else WARNING)
                status_txt = {"breakout": "פריצה מעל התנגדות", "breakdown": "שבירה מתחת לתמיכה"}.get(srl.get("status"))
                dyn = " · ".join(f"{d['name']} ${d['price']} ({d['side']})" for d in srl.get("dynamic_ma", []))
                st.markdown(
                    f"<div class='ic-card'><div style='display:flex;gap:34px;flex-wrap:wrap'>"
                    + _lvl("מחיר נוכחי", srl.get("price"), None, TEXT)
                    + _lvl("תמיכה קרובה", srl.get("support"), srl.get("dist_support_pct"), POSITIVE)
                    + _lvl("התנגדות קרובה", srl.get("resistance"), srl.get("dist_resistance_pct"), NEGATIVE)
                    + _lvl("רמת פריצה", srl.get("breakout_level"), None, SECONDARY)
                    + _lvl("רמת שבירה", srl.get("breakdown_level"), None, SECONDARY)
                    + (f"<div style='min-width:150px'><div style='color:{MUTED};font-size:12.5px'>יחס סיכון/סיכוי</div>"
                       f"<div style='font-size:22px;font-weight:700;color:{rr_c}'>{rr if rr is not None else '—'}</div>"
                       f"<div style='color:{rr_c};font-size:13px'>{rrl or ''}</div></div>")
                    + "</div>"
                    + (f"<div style='margin-top:12px;font-weight:600;color:{WARNING}'>{status_txt}</div>" if status_txt else "")
                    + f"<div class='ic-sub' style='margin-top:10px'>{srl.get('interpretation', '')}</div>"
                    + (f"<div class='ic-sub'>רמות דינמיות: {dyn}</div>" if dyn else "")
                    + f"<div class='ic-sub' style='margin-top:6px;color:{MUTED}'>הרמות הן הערכות טכניות מנתוני מחיר אמיתיים — לא רצפה/תקרה מובטחת.</div>"
                    + "</div>", unsafe_allow_html=True)

            # ---- Thesis (scenario cards) ----
            st.markdown("#### תזת השקעה — תרחישים")
            _sc_style = {"bull": ("#22c55e", "rgba(34,197,94,0.10)"),
                         "base": ("#38bdf8", "rgba(56,189,248,0.10)"),
                         "bear": ("#ef4444", "rgba(239,68,68,0.10)")}
            tt = st.columns(3)
            for col, scn in zip(tt, rep.get("scenarios", [])):
                # NOTE: loop vars must NOT shadow `sc` (scores) / `pc` (pros_cons) used below.
                ac, scn_bg = _sc_style.get(scn["key"], (PRIMARY, "rgba(56,189,248,0.10)"))
                tgt = scn["target"]
                up = tgt.get("upside")
                if up is None:
                    pill = ""
                else:
                    pcol = POSITIVE if up >= 0 else NEGATIVE
                    pill = (f"<span class='pill' style='color:{pcol};background:{pcol}22'>"
                            f"{'+' if up >= 0 else ''}{up}%</span>")
                drivers = "".join(f"<li>✓ {d}</li>" for d in scn["drivers"]) or "<li>—</li>"
                col.markdown(
                    f"<div class='scen' style='--ac:{ac};--bg:{scn_bg}'>"
                    f"<div class='s-ti'>{scn['emoji']} {scn['title']}</div>"
                    f"<div class='s-lbl'>סבירות (הערכת מודל)</div>"
                    f"<div class='s-prob'>{scn['prob']}%</div>"
                    f"<div class='s-lbl'>מחיר יעד (אנליסטים)</div>"
                    f"<div class='s-tgt'>{tgt['price']}</div>{pill}"
                    f"<div class='s-sum'>{scn['summary']}</div>"
                    f"<div class='s-lbl'>גורמים מרכזיים</div><ul>{drivers}</ul></div>",
                    unsafe_allow_html=True)
            st.caption("מחירי יעד = קונצנזוס אנליסטים (Yahoo, גבוה/ממוצע/נמוך). הסבירות היא הערכת מודל "
                       "דטרמיניסטית לפי Score V2 — אינדיקציה בלבד, לא הסתברות שוק.")
            conf = rep.get("confidence", {})
            cs = conf.get("score")
            if isinstance(cs, (int, float)):
                ccol = score_color(cs)
                st.markdown(
                    f"<div class='confmeter'><div class='ct'><span>🎯 רמת ביטחון בניתוח</span>"
                    f"<b style='color:{ccol}'>{conf.get('category', '')} · {int(cs)}/100</b></div>"
                    f"<div class='conftrack'><div class='conffill' style='width:{max(0, min(100, cs))}%;"
                    f"background:{ccol}'></div></div></div>", unsafe_allow_html=True)

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
            st.markdown("#### דעה סופית")
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
    st.markdown("### אינטליגנציית שוק — נתונים ועדויות")
    st.caption("כל המספרים נגזרים מנתוני שוק/דוחות וממנועי הניקוד הדטרמיניסטיים — ניתנים לשחזור.")
    sh = load_system_health()
    k = st.columns(4)
    k[0].metric("מניות שנסרקו", sh.get("scanned", "—"))
    k[1].metric("שלמות נתונים", fmt(sh.get("data_completeness"), "%"))
    k[2].metric("אמון ממוצע", fmt(sh.get("avg_trust")))
    k[3].metric("משיכות שנכשלו", sh.get("failed_pulls", "—"))

    # ---------- 🌍 Global markets (Phase 30) ----------
    g = load_global()
    if g.get("groups"):
        st.markdown("#### שווקים גלובליים")
        st.caption(f"עודכן {g.get('updated', '—')} · נתונים אמיתיים (Yahoo) · פרשנות דטרמיניסטית מהשינויים המחושבים בלבד.")
        _gtabs = st.tabs(["מדדים", "קריפטו", "מט\"ח", "סחורות", "אג\"ח וריביות"])
        for tab, key in zip(_gtabs, ["equity", "crypto", "fx", "commodity", "rates"]):
            with tab:
                rows_g = g["groups"].get(key, [])
                if not rows_g:
                    st.caption(NA_)
                    continue
                body = ""
                for r in rows_g:
                    p = r.get("price")
                    pv = NA_ if p is None else (f"${p:,.0f}" if str(r["symbol"]).endswith("-USD") else f"{p:,.3f}".rstrip("0").rstrip("."))
                    cells = ""
                    for dk in ("d1", "d7", "d30"):
                        dv = r.get(dk)
                        cc = MUTED if not isinstance(dv, (int, float)) else (POSITIVE if dv >= 0 else NEGATIVE)
                        cells += f"<td style='color:{cc}'>{f'{dv:+.1f}%' if isinstance(dv, (int, float)) else '—'}</td>"
                    body += (f"<tr><td><b>{r['name']}</b></td><td><b>{pv}</b></td>{cells}"
                             f"<td>{r.get('trend', '—')}</td>"
                             f"<td style='color:{SECONDARY};font-size:14px'>{r.get('interp', '')}</td></tr>")
                st.markdown(f"<table class='sectbl'><thead><tr><th>נכס</th><th>מחיר</th><th>יומי</th>"
                            f"<th>שבוע</th><th>חודש</th><th>מגמה</th><th>פרשנות</th></tr></thead>"
                            f"<tbody>{body}</tbody></table>", unsafe_allow_html=True)

    st.markdown("#### טבלת מניות מדורגת")
    cols = ["Ticker", "Name", "ScoreV2", "Score", "ScoreFundamental", "ScoreRisk",
            "TrustScore", "RiskLevel", "ExpectedUpside%", "Confidence", "DailyChange%"]
    view = df[[c for c in cols if c in df.columns]].copy().sort_values("ScoreV2", ascending=False)
    view = view.rename(columns={c: L.get(c, c) for c in view.columns})
    pcfg = {L[c]: st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d")
            for c in ("ScoreV2", "Score", "ScoreFundamental", "TrustScore")
            if c in df.columns and L.get(c) in view.columns}
    st.dataframe(view, use_container_width=True, hide_index=True, column_config=pcfg)
    st.caption("ScoreV2 = שקלול פונדמנטלי 35% · טכני 25% · סקטור 20% · חדשות 10% · סיכון 10%.")

    st.markdown("#### בקטסט — ביצועי אות הפריצה בעבר")
    _, backtest = read_outputs()
    if backtest.empty:
        st.caption("אין נתוני בקטסט.")
    else:
        st.dataframe(backtest, use_container_width=True, hide_index=True)
        st.caption("אחוז הצלחה = שיעור האיתותים שהניבו תשואה חיובית (כולל אימות Out-of-Sample).")

elif page == "⚙️ הגדרות":
    st.markdown("### הגדרות")
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
