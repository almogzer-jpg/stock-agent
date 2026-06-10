# -*- coding: utf-8 -*-
"""Stock Agent Pro — professional dark financial dashboard (Streamlit + Plotly).

Every panel is wired to REAL data from the engines:
  results.csv (indicators/scanners/ranking) · market.py (indices/sectors/regime)
  · news + sentiment · factor_scores · backtesting · alerts.
All user-facing text is Hebrew, layout is RTL. No fabricated numbers.
"""
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
from data_loader import load_ohlcv
from ranking_engine.interpret import classify
from ranking_engine.factor_scores import factor_scores
from news.headlines import get_headlines
from news.sentiment import score_headlines
from assistant import answer as assistant_answer
from dashboard.theme import DARK_CSS, style_fig, GREEN, AMBER, RED, BLUE, CARD, MUTED

st.set_page_config(page_title="Stock Agent Pro", page_icon="📈", layout="wide")
st.markdown(DARK_CSS, unsafe_allow_html=True)


# ===========================================================================
# Cached data loaders (so the UI stays responsive)
# ===========================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_results() -> pd.DataFrame:
    """Latest scan, with English column keys + group/info attached."""
    inv = {v: k for k, v in L.items()}
    df = pd.read_csv(config.RESULTS_CSV).rename(columns=inv)
    df["_group"] = [classify(r)["group"] for _, r in df.iterrows()]
    return df


@st.cache_data(ttl=1800, show_spinner=False)
def get_history(symbol: str, period: str = "6mo"):
    s = load_ohlcv(symbol, period=period)
    return None if s is None or s.empty else s["Close"]


@st.cache_data(ttl=600, show_spinner=False)
def get_market():
    return {
        "indices": market.get_indices(),
        "regime": market.market_regime_score(),
        "spx": market.get_index_history("^GSPC"),
        "ndx": market.get_index_history("^IXIC"),
        "sectors": market.get_sector_heatmap(),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def get_news_sentiment(symbol: str):
    heads = get_headlines(symbol, config.NEWS_LIMIT)
    return heads, score_headlines(heads)


@st.cache_data(ttl=300, show_spinner=False)
def read_outputs():
    """Read the latest alerts.csv + backtest_summary.xlsx written by run.py."""
    d = config.OUTPUTS_DIR
    alerts = pd.read_csv(os.path.join(d, "alerts.csv")) if os.path.exists(
        os.path.join(d, "alerts.csv")) else pd.DataFrame()
    btf = os.path.join(d, "backtest_summary.xlsx")
    backtest = pd.read_excel(btf) if os.path.exists(btf) else pd.DataFrame()
    return alerts, backtest


# Guard: if there's no scan yet (e.g. first load on Streamlit Cloud), generate
# it now — the app is self-sufficient and doesn't depend on a local PC run.
if not os.path.exists(config.RESULTS_CSV):
    st.info("טוען נתונים בפעם הראשונה — מבצע סריקה ראשונית (כ‑30–60 שניות)…")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with st.spinner("סורק את רשימת המעקב…"):
        try:
            subprocess.run([sys.executable, "run.py"], cwd=root, timeout=300,
                           env=dict(os.environ, STOCK_AGENT_DISABLE_EMAIL="1", PYTHONUTF8="1"),
                           capture_output=True, text=True)
        except Exception:
            pass
    if not os.path.exists(config.RESULTS_CSV):
        st.error("הסריקה הראשונית נכשלה. נסו לרענן את הדף.")
        st.stop()
    st.cache_data.clear()

df = load_results()
positive = df[df["_group"] == "positive"]
watch = df[df["_group"] == "watch"]
avoid = df[df["_group"] == "avoid"]
n_break = int(df["Breakout"].sum())
latest_date = df["Date"].iloc[0] if len(df) else "-"
mkt = get_market()
regime = mkt["regime"]


# ===========================================================================
# Top bar + sidebar navigation
# ===========================================================================

st.markdown(
    f"""<div class="topbar">
      <div style="font-size:20px;font-weight:800">🤖 Stock Agent <span style="color:{BLUE}">Pro</span>
        <span style="color:{MUTED};font-size:13px">v2.0</span></div>
      <div><span class="pill">● המערכת מעודכנת</span>
        <span style="color:{MUTED};margin-right:14px">{latest_date}</span></div>
    </div>""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "תצוגה",
    ["🏠 ראשי", "🤖 עוזר", "📈 מניות ופירוט", "🗺️ סקטורים",
     "🔔 התראות", "📰 חדשות", "📊 בקטסט"],
)
st.sidebar.caption(f"{len(df)} מניות · עודכן {latest_date}")

st.sidebar.divider()
if st.sidebar.button("🔄 רענן נתונים עכשיו", use_container_width=True,
                     help="מריץ סריקה מחדש על כל רשימת המעקב (כ‑30–60 שניות). ללא שליחת מייל."):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with st.spinner("מריץ סריקה מחדש על כל המניות... (כ‑30–60 שניות)"):
        # STOCK_AGENT_DISABLE_EMAIL=1 -> a manual refresh never sends email.
        env = dict(os.environ, STOCK_AGENT_DISABLE_EMAIL="1", PYTHONUTF8="1")
        try:
            proc = subprocess.run([sys.executable, "run.py"], cwd=root,
                                  capture_output=True, text=True, timeout=300, env=env)
            ok = proc.returncode == 0
        except subprocess.TimeoutExpired:
            ok, proc = False, None
    if ok:
        st.cache_data.clear()          # drop cached scan so we read fresh data
        st.sidebar.success("הנתונים עודכנו! טוען מחדש…")
        st.rerun()
    else:
        st.sidebar.error("הרענון נכשל.")
        if proc is not None:
            st.sidebar.code((proc.stderr or proc.stdout or "")[-800:])
        else:
            st.sidebar.caption("חרגה הזמן הקצוב (timeout).")


def market_strip():
    parts = []
    for ix in mkt["indices"]:
        cp = ix.get("change_pct")
        col = MUTED if cp is None else (GREEN if cp >= 0 else RED)
        sign = "+" if (cp is not None and cp >= 0) else ""
        parts.append(f"<span class='mk' style='margin-left:22px'><b>{ix['name']}</b> "
                     f"{ix.get('price','-')} <span style='color:{col}'>{sign}{cp}%</span></span>")
    st.markdown(f"<div class='card'>{''.join(parts)}</div>", unsafe_allow_html=True)


def kpi_row():
    c = st.columns(6)
    c[0].metric("🟢 מניות מומלצות", len(positive))
    c[1].metric("🚀 מועמדות לפריצה", n_break)
    c[2].metric("🟡 למעקב", len(watch))
    c[3].metric("🔴 להימנעות", len(avoid))
    best = df.iloc[0]
    c[4].metric("⭐ הבולטת היום", best["Ticker"], f"{best['DailyChange%']}%")
    c[5].metric(f"מצב שוק · {regime['label']}", regime["score"])


def recommended_table(frame, n=10):
    """Ranked table with sparkline + recommendation + risk (real data)."""
    rows = []
    for rank, (_, r) in enumerate(frame.head(n).iterrows(), start=1):
        info = classify(r)
        hist = get_history(r["Ticker"], "3mo")
        spark = list(hist.tail(40)) if hist is not None else []
        rows.append({
            "דירוג": rank, "סימול": r["Ticker"], "שם": r["Name"],
            "מחיר": r["Price"], "שינוי %": r["DailyChange%"],
            "ציון": int(r["Score"]), "המלצה": f"{info['emoji']} {info['label']}",
            "מגמה": spark, "סיבה": info["summary"], "סיכון": r["RiskLevel"],
        })
    tbl = pd.DataFrame(rows)
    st.dataframe(
        tbl, use_container_width=True, hide_index=True,
        column_config={
            "מחיר": st.column_config.NumberColumn(format="$%.2f"),
            "שינוי %": st.column_config.NumberColumn(format="%.2f%%"),
            "ציון": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "מגמה": st.column_config.LineChartColumn(width="small"),
        },
    )


def radar_avg():
    """Average factor breakdown across all stocks (real columns from the scan)."""
    fund = df["ScoreFundamental"].dropna()
    axes = ["טכני", "פונדמנטלי", "סנטימנט", "ביטחון (הפוך סיכון)", "מאקרו"]
    vals = [
        round(df["Score"].mean(), 1),
        round(fund.mean(), 1) if len(fund) else 0,
        round(df["ScoreSentiment"].mean(), 1),
        round(100 - df["ScoreRisk"].mean(), 1),
        regime["score"] if isinstance(regime["score"], (int, float)) else 0,
    ]
    fig = go.Figure(go.Scatterpolar(r=vals + [vals[0]], theta=axes + [axes[0]],
                                    fill="toself", line_color=BLUE))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])))
    return style_fig(fig, 320)


def donut_allocation():
    """Distribution of the WATCHLIST by status (real). Not a money portfolio."""
    fig = go.Figure(go.Pie(
        labels=["🟢 חיוביות", "🟡 למעקב", "🔴 להימנעות"],
        values=[len(positive), len(watch), len(avoid)], hole=0.55,
        marker_colors=[GREEN, AMBER, RED]))
    return style_fig(fig, 320)


def index_trend():
    fig = go.Figure()
    if mkt["spx"] is not None:
        fig.add_scatter(y=list(mkt["spx"]), name="S&P 500", line_color=GREEN)
    if mkt["ndx"] is not None:
        fig.add_scatter(y=list(mkt["ndx"]), name="NASDAQ", line_color=BLUE, yaxis="y2")
    fig.update_layout(yaxis2=dict(overlaying="y", side="left", showgrid=False))
    return style_fig(fig, 300)


def sector_fig():
    s = pd.DataFrame(mkt["sectors"])
    if s.empty:
        return None
    s = s.sort_values("change_pct")
    colors = [GREEN if v >= 0 else RED for v in s["change_pct"]]
    fig = go.Figure(go.Bar(x=s["change_pct"], y=s["sector"], orientation="h",
                           marker_color=colors,
                           text=[f"{v:+.2f}%" for v in s["change_pct"]]))
    return style_fig(fig, 380)


# ===========================================================================
# Pages
# ===========================================================================

if page == "🏠 ראשי":
    kpi_row()
    market_strip()
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("#### ⭐ מניות מומלצות להיום")
        recommended_table(positive, 10)
    with col2:
        st.markdown("#### 🎯 פיזור ציון לפי קטגוריות")
        st.plotly_chart(radar_avg(), use_container_width=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### 📈 מגמת מדדים (6 חודשים)")
        st.plotly_chart(index_trend(), use_container_width=True)
    with col4:
        st.markdown("#### 🧩 פילוח רשימת המעקב")
        st.plotly_chart(donut_allocation(), use_container_width=True)
        st.caption("פילוח לפי סטטוס (לא תיק כספי — אין תיק מחובר).")

elif page == "🤖 עוזר":
    st.markdown("#### 🤖 עוזר חכם — שאל שאלה על המניות שלך")
    st.caption("דוגמאות: \"מה המניות הכי חזקות?\" · \"מה הציון של NVDA?\" · "
               "\"כמה מועמדות לפריצה?\" · \"למה להימנע מ-META?\" · \"מה מצב השוק?\"")
    if "chat" not in st.session_state:
        st.session_state.chat = [
            ("assistant", "שלום! 👋 אני העוזר של סוכן המניות. שאל אותי בעברית על "
                          "תוצאות הסריקה — למשל \"מה המניות הכי חזקות היום?\"")
        ]
    # Render conversation history.
    for role, msg in st.session_state.chat:
        with st.chat_message(role, avatar=("🤖" if role == "assistant" else "🙂")):
            st.markdown(msg, unsafe_allow_html=True)
    # Input.
    q = st.chat_input("הקלד שאלה בעברית…")
    if q:
        st.session_state.chat.append(("user", q))
        with st.chat_message("user", avatar="🙂"):
            st.markdown(q)
        ans = assistant_answer(q, df, {"indices": mkt["indices"], "regime": regime})
        st.session_state.chat.append(("assistant", ans))
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(ans, unsafe_allow_html=True)

elif page == "📈 מניות ופירוט":
    st.markdown("#### 📋 כל המניות")
    recommended_table(df, len(df))
    st.divider()
    st.markdown("#### 🔍 כרטיס מניה")
    sym = st.selectbox("בחר מניה", df["Ticker"].tolist())
    r = df[df["Ticker"] == sym].iloc[0]
    info = classify(r)
    heads, news_sent = get_news_sentiment(sym)
    hist = get_history(sym, "6mo")
    fs = factor_scores(r, closes=list(hist.tail(60)) if hist is not None else None,
                       fundamentals=r, news_sent=news_sent)

    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"### {info['emoji']} {sym} — {r['Name']}")
        st.markdown(f"<div style='color:{info['color']};font-weight:bold;font-size:17px'>"
                    f"{info['summary']}</div><div style='color:{MUTED}'>{info['detail']}</div>",
                    unsafe_allow_html=True)
        if hist is not None:
            fig = go.Figure(go.Scatter(y=list(hist), line_color=BLUE, fill="tozeroy"))
            st.plotly_chart(style_fig(fig, 280), use_container_width=True)
    with right:
        # Factor radar (per stock) — all real.
        axes = ["טכני", "פונדמנטלי", "חדשות", "סנטימנט", "ביטחון"]
        vals = [fs["technical"], fs["fundamental"] or 0, fs["news"] or 50,
                fs["sentiment"], 100 - fs["risk"]]
        fig = go.Figure(go.Scatterpolar(r=vals + [vals[0]], theta=axes + [axes[0]],
                                        fill="toself", line_color=GREEN))
        fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])))
        st.plotly_chart(style_fig(fig, 300), use_container_width=True)

    m = st.columns(5)
    m[0].metric("טכני", fs["technical"])
    m[1].metric("פונדמנטלי", fs["fundamental"] if fs["fundamental"] is not None else "אין נתון")
    m[2].metric("חדשות", fs["news"] if fs["news"] is not None else 50)
    m[3].metric("סנטימנט", fs["sentiment"])
    m[4].metric("רמת סיכון", r["RiskLevel"])

    action = {"positive": "✅ קנייה / מעקב חיובי", "watch": "🟡 מעקב",
              "avoid": "🔴 להימנעות"}[info["group"]]
    st.markdown(f"<div class='card'><b>פעולה מוצעת:</b> {action}</div>", unsafe_allow_html=True)
    if heads:
        st.markdown("**כותרות אחרונות:**")
        for h in heads[:5]:
            st.markdown(f"- {h['title']}  <span style='color:{MUTED}'>· {h['publisher']}</span>",
                        unsafe_allow_html=True)

elif page == "🗺️ סקטורים":
    st.markdown("#### 🗺️ מפת חום סקטורים (שינוי יומי, ETF מייצג)")
    fig = sector_fig()
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("נתוני סקטורים לא זמינים כרגע.")

elif page == "🔔 התראות":
    st.markdown("#### 🔔 התראות אחרונות")
    alerts, _ = read_outputs()
    if alerts.empty:
        st.caption("אין התראות בהרצה האחרונה.")
    else:
        st.dataframe(alerts, use_container_width=True, hide_index=True)

elif page == "📰 חדשות":
    st.markdown("#### 📰 חדשות אחרונות (מניות מובילות)")
    for _, r in positive.head(6).iterrows():
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
        st.caption("אין נתוני בקטסט. הריצו `python run.py`.")
    else:
        st.dataframe(backtest, use_container_width=True, hide_index=True)
        st.caption("אחוז הצלחה = שיעור האיתותים שהניבו תשואה חיובית בטווח שנמדד.")

st.caption("לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")
