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
from dashboard.theme import DARK_CSS, style_fig, GREEN, AMBER, RED, BLUE, CARD, MUTED, TEXT

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
    ["🏠 ראשי (60 שניות)", "🔭 סורק שוק", "🤖 עוזר", "📈 מניות ופירוט", "🗺️ סקטורים",
     "💼 תיק", "🧭 החלטות תיק", "🛡️ אמון ואימות", "🔔 התראות", "📰 חדשות", "📊 בקטסט"],
)
st.sidebar.caption(f"{len(df)} מניות · עודכן {latest}")
st.sidebar.divider()
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

if page.startswith("🏠"):
    regime = mkt.get("regime", {})
    fng = mkt.get("fear_greed", {})
    breadth = mkt.get("breadth", {})
    indices = mkt.get("indices", [])
    ins = mkt.get("insights", {})

    # --- AI Insights briefing (Phase 11) ---
    if ins:
        import re
        def _b(s):  # markdown **bold** -> HTML bold (we're inside an HTML card)
            return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s or "")
        st.markdown(
            f"""<div class="card" style="border-right:5px solid {BLUE}">
              <div style="font-size:18px;font-weight:800">📝 תובנות היום <span style="color:{MUTED};font-size:12px">· מופק אוטומטית</span></div>
              <div style="color:{TEXT};margin-top:6px;line-height:1.7">
                <p>🌐 <b>שוק:</b> {_b(ins.get('market',''))}</p>
                <p>💎 <b>הזדמנויות:</b> {_b(ins.get('opportunities',''))}</p>
                <p>⚠️ <b>סיכונים:</b> {_b(ins.get('risks',''))}</p>
                <p>🔄 <b>רוטציה:</b> {_b(ins.get('rotation',''))}</p>
              </div>
            </div>""", unsafe_allow_html=True)

    # --- Market Overview ---
    st.markdown("### 🌐 סקירת שוק")
    reg_score = regime.get("score")
    reg_label = regime.get("label", "—")
    reg_color = (GREEN if isinstance(reg_score, (int, float)) and reg_score >= 60
                 else RED if isinstance(reg_score, (int, float)) and reg_score < 40 else AMBER)

    top = st.columns([2, 1, 1])
    with top[0]:
        st.markdown(
            f"""<div class="card">
              <div style="color:{MUTED}">מצב שוק (Market Regime)</div>
              <div style="font-size:34px;font-weight:800;color:{reg_color}">{fmt(reg_score)} · {reg_label}</div>
              <div style="color:{MUTED};font-size:13px;margin-top:6px">
                <b>למה?</b> מבוסס על S&P 500 מול ממוצעים נעים (200/50) ורמת VIX.
                רוחב שוק: {fmt(breadth.get('above50'),'%')} מהמניות מעל ממוצע 50,
                {fmt(breadth.get('above200'),'%')} מעל ממוצע 200,
                {fmt(breadth.get('advancers'))}/{fmt(breadth.get('decliners'))} עולות/יורדות.
              </div>
            </div>""", unsafe_allow_html=True)
        # Indices strip
        cells = []
        for ix in indices:
            cp = ix.get("change_pct")
            col = MUTED if cp is None else (GREEN if cp >= 0 else RED)
            sign = "+" if (cp is not None and cp >= 0) else ""
            cells.append(f"<span style='margin-left:20px'><b style='color:{TEXT}'>{ix['name']}</b> "
                         f"{fmt(ix.get('price'))} <span style='color:{col}'>{sign}{fmt(cp)}%</span></span>")
        st.markdown(f"<div class='card'>{''.join(cells)}</div>", unsafe_allow_html=True)
        # S&P trend
        spx = mkt.get("spx_hist", [])
        if spx:
            fig = go.Figure(go.Scatter(y=spx, line_color=GREEN, fill="tozeroy"))
            fig.update_layout(title="S&P 500 · 6 חודשים")
            st.plotly_chart(style_fig(fig, 220), use_container_width=True)
    with top[1]:
        st.markdown("<div class='card' style='text-align:center'>"
                    "<div style='color:#9fb3d1'>מד פחד / חמדנות</div>"
                    "<div style='font-size:11px;color:#6b86ad'>מדד קנייני מחושב</div></div>",
                    unsafe_allow_html=True)
        fear_greed_gauge(fng)
    with top[2]:
        st.metric("🟢 מומלצות", len(positive))
        st.metric("🚀 פריצה", n_break)
        st.metric("🟡 מעקב", len(watch))
        st.metric("🔴 הימנעות", len(avoid))

    with st.expander("ℹ️ איך מחושב מד הפחד/חמדנות?"):
        st.write(fng.get("method", "—"))
        st.write("**רוחב שוק:** " + breadth.get("method", "—"))

    st.divider()

    # --- Top Opportunities ---
    st.markdown("### 💎 ההזדמנויות הטובות ביותר היום")
    ranked = positive.sort_values("ScoreV2", ascending=False) if not positive.empty \
        else df.sort_values("ScoreV2", ascending=False)
    if ranked.empty:
        st.caption("אין הזדמנויות חיוביות היום.")
    else:
        t3, t5, t10 = st.tabs(["Top 3", "Top 5", "Top 10"])
        for tab, k in [(t3, 3), (t5, 5), (t10, 10)]:
            with tab:
                shown = ranked.head(k)
                if shown.empty:
                    st.caption("אין מספיק מניות.")
                for rank, (_, r) in enumerate(shown.iterrows(), start=1):
                    opportunity_card(rank, r)
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
        # --- Headline analytics ---
        bm = pf.get("benchmark", {})
        c = st.columns(4)
        c[0].metric("💰 שווי תיק", f"${pf['total_value']:,.0f}",
                    f"{pf['total_pl_pct']:+.2f}% (${pf['total_pl']:,.0f})")
        c[1].metric("📅 שינוי יומי", f"{pf['daily_change_pct']:+.2f}%")
        c[2].metric("📈 חודשי", f"{pf['monthly_change_pct']:+.2f}%")
        ytd_delta = None
        if bm.get("ret_ytd") is not None and pf.get("ytd_pct") is not None:
            ytd_delta = f"{pf['ytd_pct'] - bm['ret_ytd']:+.2f}% מול S&P"
        c[3].metric("🗓️ YTD", f"{fmt(pf.get('ytd_pct'),'%')}", ytd_delta)

        # --- Health + exposures ---
        hcol, ecol = st.columns([1, 2])
        with hcol:
            h = pf.get("health", {})
            hs = h.get("score")
            hcolor = GREEN if (hs or 0) >= 66 else (AMBER if (hs or 0) >= 40 else RED)
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=hs or 0,
                number={"font": {"color": TEXT}},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": hcolor}}))
            style_fig(fig, 200)
            st.markdown("**🩺 ציון בריאות התיק**")
            st.plotly_chart(fig, use_container_width=True)
            for f in h.get("factors", []):
                st.caption(f"• {f}")
        with ecol:
            e1, e2, e3 = st.columns(3)
            for col, title, key in [(e1, "סקטורים", "sector"),
                                    (e2, "סיכון", "risk"), (e3, "שווי שוק", "cap")]:
                exp = pf["exposures"].get(key, {})
                if exp:
                    fig = go.Figure(go.Pie(labels=list(exp.keys()), values=list(exp.values()),
                                           hole=0.5))
                    fig.update_layout(title=title, showlegend=False)
                    fig.update_traces(textinfo="label+percent", textfont_size=10)
                    col.plotly_chart(style_fig(fig, 220), use_container_width=True)

        # --- Portfolio risk (Part 2) ---
        prisk = pf.get("risk", {})
        if prisk:
            st.markdown("##### 🛡️ סיכון תיק")
            rc = st.columns(4)
            rc[0].metric("ביתא תיק", fmt(prisk.get("weighted_beta")))
            rc[1].metric("תנודתיות משוקללת", fmt(prisk.get("weighted_volatility"), "%"))
            rc[2].metric("ריכוז (0–100)", fmt(prisk.get("concentration_risk")))
            rc[3].metric("פוזיציות אפקטיביות", fmt(prisk.get("effective_positions")))
            for w in prisk.get("warnings", []):
                st.markdown(f"<div class='card' style='border-right:4px solid {AMBER};padding:8px 12px'>"
                            f"⚠️ {w}</div>", unsafe_allow_html=True)
            corr = pf.get("correlation", {}).get("matrix", {})
            if corr and len(corr) >= 2:
                tk = list(corr.keys())
                z = [[corr[a].get(b, 0) for b in tk] for a in tk]
                fig = go.Figure(go.Heatmap(z=z, x=tk, y=tk, zmin=-1, zmax=1,
                                           colorscale="RdYlGn_r",
                                           text=z, texttemplate="%{text:.2f}", textfont_size=10))
                fig.update_layout(title="מטריצת קורלציה (תשואות יומיות)")
                st.plotly_chart(style_fig(fig, 360), use_container_width=True)
            hp = pf.get("correlation", {}).get("high_pairs", [])
            if hp:
                st.caption("זוגות מתואמים גבוה (ריכוז סמוי): " +
                           " · ".join(f"{p['a']}–{p['b']} ({p['corr']})" for p in hp))

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

st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")
