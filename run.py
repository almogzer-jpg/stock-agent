#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stock Agent — daily orchestrator.

Pipeline:
    watchlist -> load OHLCV -> indicators -> scanner + ranking
              -> (optional fundamentals/news) -> export CSV/XLSX
              -> alerts -> Hebrew summary

Run:
    python run.py
"""
import os
import sys

# Force UTF-8 console output so the Hebrew summary / emoji render on Windows
# terminals (which default to a legacy code page such as cp1255).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Make this directory the package root so the module imports below resolve.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import base64
import json
from datetime import datetime

import pandas as pd

import config
import proprietary
import portfolio
import technicals
import insights as insights_mod
from data_loader import load_ohlcv
from names import get_company_name
from indicators.technical import compute_indicators
from scanners.breakout import is_breakout
from ranking_engine.score import score_stock
from ranking_engine.interpret import classify
from ranking_engine.factor_scores import factor_scores
from ranking_engine.composite import composite_score
from news.sentiment import score_headlines
from charts import sparkline_png
from fundamentals.fundamentals import get_fundamentals
from news.headlines import get_headlines
from backtesting.backtester import backtest_symbol, backtest_signal
import market
import risk as risk_engine
import decisions as decision_engine
import trust as trust_engine
import events as events_mod
from alerts.center import build_alerts
from alerts.notifier import Notifier
from alerts.email_notifier import EmailNotifier


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def load_watchlist(path: str) -> list[str]:
    """One ticker per line; '#' and blank lines ignored; upper-cased, de-duped."""
    if not os.path.exists(path):
        raise SystemExit(f"Watchlist not found: {path}")
    out, seen = [], set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip().upper()
            if not s or s.startswith("#") or s in seen:
                continue
            seen.add(s)
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Export (analysis snapshot — explicitly a CSV/Excel export, so static values)
# ---------------------------------------------------------------------------

def export(df: pd.DataFrame) -> None:
    """Write the results table to CSV (utf-8-sig) and Excel (auto-sized cols).

    Columns are renamed to Hebrew labels for the user-facing files; the
    in-memory df keeps its English keys for the rest of the pipeline.
    """
    out = df.rename(columns=config.COLUMN_LABELS_HE)
    out.to_csv(config.RESULTS_CSV, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(config.RESULTS_XLSX, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="סריקה")
        ws = writer.sheets["סריקה"]
        for cells in ws.columns:
            width = max(
                (len(str(c.value)) for c in cells if c.value is not None),
                default=8,
            )
            ws.column_dimensions[cells[0].column_letter].width = width + 2
    print(f"\nנשמר: {config.RESULTS_CSV}")
    print(f"נשמר: {config.RESULTS_XLSX}")


# ---------------------------------------------------------------------------
# Email report (HTML, RTL) — grouped by status, with explanations + charts
# ---------------------------------------------------------------------------

def _stock_card(r, info, chart_src: str | None) -> str:
    """Build one HTML 'card' for a stock: status, plain summary, facts, chart.

    `chart_src` is the value for the <img src>: a "cid:..." reference (email)
    or a "data:image/png;base64,..." URI (standalone file), or None for no chart.
    """
    chart_cell = (
        f"<td width='185' valign='middle' align='center'>"
        f"<img src='{chart_src}' width='175' alt='גרף'></td>"
        if chart_src else ""
    )
    return f"""
    <div style="border-right:5px solid {info['color']};background:#f7f9fb;
                padding:12px 14px;margin:10px 0;border-radius:6px">
      <table width="100%" style="border-collapse:collapse"><tr>
        <td valign="top">
          <div style="font-size:16px">
            <b>{r['Ticker']}</b> — {r['Name']}
            &nbsp;<span style="color:{info['color']}">{info['emoji']} {info['label']}</span>
          </div>
          <div style="color:#555;margin:4px 0">ציון <b>{r['Score']}</b>/100 · מחיר ${r['Price']}</div>
          <div style="font-weight:bold;color:{info['color']};margin:6px 0">{info['summary']}</div>
          <div style="color:#666;font-size:13px;line-height:1.6">{info['detail']}</div>
        </td>
        {chart_cell}
      </tr></table>
    </div>"""


def render_report_html(df: pd.DataFrame, closes_map: dict, embed: str = "cid"):
    """Render the daily report as RTL HTML.

    embed="cid"    -> charts referenced as cid:... ; returns (html, images)
                      where images maps content-id -> PNG bytes (for email).
    embed="base64" -> charts embedded inline as data URIs; images is empty
                      (self-contained file you can open in any browser).
    """
    today = datetime.now().strftime(config.DATE_FMT)

    df = df.copy()
    df["_group"] = [classify(r)["group"] for _, r in df.iterrows()]
    positive = df[df["_group"] == "positive"]
    watch = df[df["_group"] == "watch"]
    avoid = df[df["_group"] == "avoid"]

    n_break = int(df["Breakout"].sum())
    standout = df.iloc[0]
    images: dict = {}

    def chart_src(ticker):
        """Return the <img src> for a ticker's sparkline, or None."""
        if ticker not in closes_map:
            return None
        try:
            png = sparkline_png(closes_map[ticker])
        except Exception:
            return None
        if embed == "cid":
            images[f"chart_{ticker}"] = png
            return f"cid:chart_{ticker}"
        b64 = base64.b64encode(png).decode("ascii")
        return f"data:image/png;base64,{b64}"

    def section(title, frame, with_charts):
        if frame.empty:
            return ""
        cards = ""
        for _, r in frame.iterrows():
            info = classify(r)
            src = chart_src(r["Ticker"]) if with_charts else None
            cards += _stock_card(r, info, src)
        return f'<h3 style="margin-top:22px">{title}</h3>{cards}'

    bottom_line = f"""
    <div style="background:#1f3b57;color:#fff;padding:14px 16px;border-radius:8px">
      <div style="font-size:17px;font-weight:bold;margin-bottom:6px">השורה התחתונה להיום</div>
      <div style="line-height:1.8">
        🟢 {len(positive)} מניות במומנטום חיובי (מתוכן {n_break} מועמדות לפריצה) ·
        🟡 {len(watch)} למעקב · 🔴 {len(avoid)} להימנעות.<br>
        הבולטת היום: <b>{standout['Ticker']}</b> ({standout['Name']}) — ציון {standout['Score']}/100.
      </div>
    </div>"""

    avoid_rows = ""
    for _, r in avoid.iterrows():
        avoid_rows += (f"<div style='padding:4px 0;color:#555'>🔴 <b>{r['Ticker']}</b> "
                       f"{r['Name']} — {classify(r)['summary']}</div>")
    avoid_html = (f'<h3 style="margin-top:22px">🔴 להימנעות ({len(avoid)})</h3>{avoid_rows}'
                  if not avoid.empty else "")

    html = f"""<html><head><meta charset="utf-8"></head><body dir="rtl"
        style="font-family:Arial,Helvetica,sans-serif;color:#222;max-width:680px;margin:auto">
      <h2>📈 סוכן מניות — דוח יומי ({today})</h2>
      {bottom_line}
      {section(f"🟢 מומנטום חיובי ({len(positive)})", positive, with_charts=True)}
      {section(f"🟡 למעקב ({len(watch)})", watch, with_charts=True)}
      {avoid_html}
      <p style="color:#999;font-size:12px;margin-top:26px;border-top:1px solid #eee;padding-top:12px">
        הופק אוטומטית ע״י Stock Agent · נתונים מ‑Yahoo Finance ·
        לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.
      </p>
    </body></html>"""

    return html, images


def build_report_email(df: pd.DataFrame, closes_map: dict):
    """Build the daily report email: (subject, html, text, images)."""
    today = datetime.now().strftime(config.DATE_FMT)
    html, images = render_report_html(df, closes_map, embed="cid")

    grp = df.assign(_g=[classify(r)["group"] for _, r in df.iterrows()])
    positive, watch, avoid = (grp[grp["_g"] == g] for g in ("positive", "watch", "avoid"))
    n_break = int(df["Breakout"].sum())
    subject = (f"📈 דוח מניות {today} — "
               f"{len(positive)} חיוביות, {n_break} מועמדות לפריצה")

    # Plain-text fallback.
    lines = [f"סוכן מניות — דוח יומי {today}", ""]
    for grp_name, frame in [("🟢 מומנטום חיובי", positive),
                            ("🟡 למעקב", watch), ("🔴 להימנעות", avoid)]:
        if frame.empty:
            continue
        lines.append(f"{grp_name} ({len(frame)}):")
        for _, r in frame.iterrows():
            lines.append(f"  {r['Ticker']} {r['Name']} | ציון {r['Score']} | {classify(r)['summary']}")
        lines.append("")
    text = "\n".join(lines)

    return subject, html, text, images


# ---------------------------------------------------------------------------
# Hebrew daily summary
# ---------------------------------------------------------------------------

def hebrew_summary(df: pd.DataFrame) -> None:
    """Print a Hebrew report: top 10, breakout candidates, and stocks to avoid."""
    today = datetime.now().strftime(config.DATE_FMT)

    print("\n" + "=" * 60)
    print(f"  סיכום סריקת מניות יומי — {today}")
    print("=" * 60)

    # Top 10 by score
    print("\n📊 עשרת המניות המובילות (לפי ציון):")
    for rank, (_, r) in enumerate(df.head(10).iterrows(), start=1):
        print(
            f"  {rank:>2}. {r['Ticker']:<6} {str(r['Name'])[:24]:<24} | "
            f"ציון: {r['Score']:>3} | RSI: {r['RSI14']:>4} | "
            f"מרחק משיא: {r['DistFromHigh%']}%"
        )

    # Breakout candidates
    breakouts = df[df["Breakout"] == True]  # noqa: E712
    print(f"\n🚀 מועמדים לפריצה ({len(breakouts)}):")
    if breakouts.empty:
        print("  אין מועמדים לפריצה היום.")
    else:
        for _, r in breakouts.iterrows():
            print(
                f"  • {r['Ticker']:<6} {str(r['Name'])[:24]:<24} | ציון: {r['Score']:>3} | "
                f"נפח: x{r['VolRatio']} | RSI: {r['RSI14']}"
            )

    # Stocks to avoid (below 200-day MA, weak RSI, or low score)
    avoid = df[(df["Price"] < df["MA200"]) | (df["RSI14"] < 40) | (df["Score"] < 35)]
    print(f"\n⚠️  מניות להימנע מהן ({len(avoid)}):")
    if avoid.empty:
        print("  אין מניות חלשות במיוחד היום.")
    else:
        for _, r in avoid.iterrows():
            reason = []
            if r["Price"] < r["MA200"]:
                reason.append("מתחת לממוצע 200")
            if r["RSI14"] < 40:
                reason.append("RSI חלש")
            if r["Score"] < 35:
                reason.append("ציון נמוך")
            print(f"  • {r['Ticker']:<6} {str(r['Name'])[:24]:<24} | ציון: {r['Score']:>3} | {', '.join(reason)}")

    print("\n" + "=" * 60)
    print("  הערה: לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Static dark dashboard snapshot (dashboard/index.html)
# ---------------------------------------------------------------------------

def build_static_dashboard_html(df: pd.DataFrame, closes_map: dict,
                                indices: list, regime: dict) -> str:
    """Build a self-contained dark-theme HTML snapshot of the dashboard.

    Real data only: KPIs from the scan, market strip from yfinance indices,
    a ranked opportunities table with embedded sparklines, and grouped cards.
    """
    today = datetime.now().strftime(config.DATE_FMT)
    g = df.assign(_g=[classify(r)["group"] for _, r in df.iterrows()])
    positive = g[g["_g"] == "positive"]
    watch = g[g["_g"] == "watch"]
    avoid = g[g["_g"] == "avoid"]
    n_break = int(df["Breakout"].sum())
    best = df.iloc[0]

    def chip(label, value, color):
        return (f"<div style='background:#16213a;border:1px solid #233456;border-radius:10px;"
                f"padding:14px 18px;min-width:130px'>"
                f"<div style='font-size:30px;font-weight:800;color:{color}'>{value}</div>"
                f"<div style='color:#9fb3d1;font-size:13px'>{label}</div></div>")

    kpis = "".join([
        chip("מניות מומלצות", len(positive), "#36d399"),
        chip("מועמדות לפריצה", n_break, "#36d399"),
        chip("למעקב", len(watch), "#fbbd23"),
        chip("להימנעות", len(avoid), "#f87272"),
        chip("התראות", n_break, "#60a5fa"),
        chip(f"מצב שוק · {regime.get('label','')}", regime.get("score", "-"), "#36d399"),
    ])

    # Market strip.
    mk = ""
    for ix in indices:
        cp = ix.get("change_pct")
        col = "#9fb3d1" if cp is None else ("#36d399" if cp >= 0 else "#f87272")
        sign = "" if (cp is None or cp < 0) else "+"
        mk += (f"<span style='margin-left:22px'><b style='color:#cfe0f5'>{ix['name']}</b> "
               f"{ix.get('price','-')} <span style='color:{col}'>{sign}{cp}%</span></span>")

    def reco_rows(frame):
        out = ""
        for rank, (_, r) in enumerate(frame.iterrows(), start=1):
            info = classify(r)
            cp = r["DailyChange%"]
            ccol = "#36d399" if cp >= 0 else "#f87272"
            try:
                b64 = base64.b64encode(sparkline_png(closes_map.get(r["Ticker"], []))).decode("ascii")
                spark = f"<img src='data:image/png;base64,{b64}' width='120'>"
            except Exception:
                spark = ""
            out += (
                f"<tr style='border-bottom:1px solid #233456'>"
                f"<td>{rank}</td><td><b>{r['Ticker']}</b></td><td>{r['Name']}</td>"
                f"<td>${r['Price']}</td><td style='color:{ccol}'>{'+' if cp>=0 else ''}{cp}%</td>"
                f"<td><b>{r['Score']}</b></td>"
                f"<td style='color:{info['color']}'>{info['emoji']} {info['label']}</td>"
                f"<td>{spark}</td><td style='color:#9fb3d1;font-size:12px'>{info['summary']}</td>"
                f"<td>{r['RiskLevel']}</td></tr>"
            )
        return out

    th = ("<tr style='color:#9fb3d1;text-align:right;border-bottom:2px solid #233456'>"
          "<th>#</th><th>סימול</th><th>שם</th><th>מחיר</th><th>שינוי</th><th>ציון</th>"
          "<th>המלצה</th><th>מגמה</th><th>סיבה</th><th>סיכון</th></tr>")

    return f"""<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stock Agent — לוח בקרה</title></head>
<body style="margin:0;background:#0e1726;color:#e6eefb;font-family:Arial,Helvetica,sans-serif">
  <div style="background:#0b1220;border-bottom:1px solid #233456;padding:14px 24px;
              display:flex;justify-content:space-between;align-items:center">
    <div style="font-size:20px;font-weight:800">🤖 Stock Agent <span style="color:#60a5fa">Pro</span></div>
    <div style="color:#9fb3d1">המערכת מעודכנת · {today}</div>
  </div>
  <div style="padding:18px 24px;color:#9fb3d1;border-bottom:1px solid #233456">{mk}</div>
  <div style="padding:22px 24px">
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">{kpis}</div>
    <div style="background:#16213a;border:1px solid #233456;border-radius:12px;padding:18px">
      <h3 style="margin:0 0 12px">⭐ מניות מומלצות להיום</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px">{th}{reco_rows(positive)}</table>
    </div>
    <p style="color:#6b86ad;font-size:12px;margin-top:18px">
      הופק אוטומטית · נתונים מ‑Yahoo Finance · לצרכי מידע בלבד, אין לראות בכך ייעוץ השקעות.
    </p>
  </div>
</body></html>"""


# ---------------------------------------------------------------------------
# Timestamped deliverables (data/outputs)
# ---------------------------------------------------------------------------

def _write_xlsx(df_he: pd.DataFrame, path: str, sheet: str) -> None:
    """Write a DataFrame to a single-sheet, auto-sized Excel file."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_he.to_excel(writer, index=False, sheet_name=sheet)
        ws = writer.sheets[sheet]
        for cells in ws.columns:
            width = max((len(str(c.value)) for c in cells if c.value is not None), default=8)
            ws.column_dimensions[cells[0].column_letter].width = width + 2


# Hebrew labels for the backtest summary columns.
BACKTEST_LABELS_HE = {
    "Ticker": "סימול", "Name": "שם", "occurrences": "מספר מופעים",
    "win_rate": "אחוז הצלחה %", "avg_return": "תשואה ממוצעת %",
    "median_return": "תשואה חציונית %", "max_drawdown": "ירידה מקס׳ %",
    "benchmark_rel": "מול בנצ׳מרק %", "avg_holding": "החזקה ממוצעת (ימים)",
    "is_win_rate": "IS הצלחה %", "oos_win_rate": "OOS הצלחה %",
    "oos_avg_return": "OOS תשואה %", "confidence": "רמת ביטחון",
}


def write_timestamped_outputs(df: pd.DataFrame, closes_map: dict,
                              alerts_history: list, backtest_rows: list,
                              indices: list, regime: dict) -> list:
    """Write every deliverable into data/outputs/ (timestamped + 'latest'),
    and regenerate the static dashboard at dashboard/index.html.

    For each artifact we write two files: a timestamped historical copy
    (YYYY-MM-DD_HHMM) and a fixed-name 'latest' copy with no timestamp:
        daily_report.html/.xlsx, opportunities.csv, alerts.csv, backtest_summary.xlsx
    """
    ts = datetime.now().strftime("%Y-%m-%d_%H%M")
    d = config.OUTPUTS_DIR
    written = []

    def both(name, ext):
        """Return (timestamped_path, latest_path) for an artifact name."""
        return (os.path.join(d, f"{name}_{ts}{ext}"), os.path.join(d, f"{name}{ext}"))

    # 1) Self-contained HTML report (base64 charts -> opens in any browser).
    html, _ = render_report_html(df, closes_map, embed="base64")
    for p in both("daily_report", ".html"):
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(html)
        written.append(p)

    # 2) Full results as Excel (Hebrew headers).
    df_he = df.rename(columns=config.COLUMN_LABELS_HE)
    for p in both("daily_report", ".xlsx"):
        _write_xlsx(df_he, p, "סריקה")
        written.append(p)

    # 3) Opportunities = the positive (🟢) group only.
    groups = df.assign(_g=[classify(r)["group"] for _, r in df.iterrows()])
    opp = groups[groups["_g"] == "positive"].drop(columns="_g").rename(columns=config.COLUMN_LABELS_HE)
    for p in both("opportunities", ".csv"):
        opp.to_csv(p, index=False, encoding="utf-8-sig")
        written.append(p)

    # 4) Alerts fired this run.
    alerts_df = (pd.DataFrame(alerts_history) if alerts_history
                 else pd.DataFrame(columns=["זמן", "רמה", "הודעה"]))
    for p in both("alerts", ".csv"):
        alerts_df.to_csv(p, index=False, encoding="utf-8-sig")
        written.append(p)

    # 5) Backtest summary (historical performance of the breakout signal).
    bt_df = (pd.DataFrame(backtest_rows).rename(columns=BACKTEST_LABELS_HE)
             if backtest_rows else pd.DataFrame(columns=list(BACKTEST_LABELS_HE.values())))
    for p in both("backtest_summary", ".xlsx"):
        _write_xlsx(bt_df, p, "בקטסט")
        written.append(p)

    # 6) Static dark dashboard snapshot at dashboard/index.html.
    try:
        index_html = build_static_dashboard_html(df, closes_map, indices, regime)
        with open(config.DASHBOARD_INDEX, "w", encoding="utf-8") as fh:
            fh.write(index_html)
        written.append(config.DASHBOARD_INDEX)
    except Exception as exc:
        print(f"  ! נכשלה יצירת dashboard/index.html: {exc}")

    print(f"\nנכתבו {len(written)} קבצי פלט (מתוארכים + 'latest' + index.html).")
    return written


# ---------------------------------------------------------------------------
# Portfolio helpers
# ---------------------------------------------------------------------------

def _returns(close) -> dict:
    """Daily / 1-month / YTD % returns from a Close series (NaN-safe)."""
    close = close.dropna()
    out = {"daily": None, "m1": None, "ytd": None}
    if len(close) >= 2:
        out["daily"] = round(float(close.iloc[-1] / close.iloc[-2] - 1) * 100, 2)
    if len(close) > 22:
        out["m1"] = round(float(close.iloc[-1] / close.iloc[-23] - 1) * 100, 2)
    year = datetime.now().year
    ytd_base = close[close.index.year == year]
    if len(ytd_base):
        out["ytd"] = round(float(close.iloc[-1] / ytd_base.iloc[0] - 1) * 100, 2)
    return out


def build_portfolio_payload(sectors=None, regime_label=""):
    """Load holdings, fetch each one's real data, and compute the analytics
    + Risk (Part 2) + Decisions (Part 3)."""
    sectors = sectors or []
    holdings = portfolio.load_holdings(config.PORTFOLIO_CSV)
    if not holdings:
        return {"empty": True}
    print(f"\nמחשב תיק ({len(holdings)} החזקות)...")
    mkt_df = load_ohlcv("^GSPC")
    mkt_close = mkt_df["Close"] if mkt_df is not None else None
    positions, closes_pf = [], {}
    for h in holdings:
        sym = h["ticker"]
        pdf = load_ohlcv(sym)
        if pdf is None:
            print(f"  ! {sym}: אין נתונים — דולג")
            continue
        close = pdf["Close"]
        m = compute_indicators(pdf)
        if m is None:
            continue
        m["Breakout"] = is_breakout(m)
        m["Score"] = score_stock(m)
        rets = _returns(close)
        fund = get_fundamentals(sym)
        fs = factor_scores(m, closes=close.tail(60).tolist(), fundamentals=fund)
        rp = risk_engine.risk_profile(close, mkt_close)   # beta / vol / maxDD
        closes_pf[sym] = close.tail(252)
        # Composite v2 + decision inputs for this holding.
        m["ScoreFundamental"] = fs["fundamental"]
        m["ScoreSentiment"] = fs["sentiment"]
        m["ScoreRisk"] = rp["risk_score"] if rp["risk_score"] is not None else fs["risk"]
        sec_score = market.sector_score_for(fund.get("Sector"), sectors)
        news_sc = (score_headlines(get_headlines(sym, config.NEWS_LIMIT))["score"]
                   if config.ENABLE_NEWS else 50)
        comp = composite_score(technical=m["Score"], fundamental=fs["fundamental"],
                               sector=sec_score, news=news_sc, risk=m["ScoreRisk"])
        positions.append({
            "ticker": sym, "name": get_company_name(sym),
            "quantity": h["quantity"], "avg_cost": h["avg_cost"],
            "price": round(float(close.iloc[-1]), 2),
            "daily_change_pct": rets["daily"], "ret_1m": rets["m1"], "ret_ytd": rets["ytd"],
            "sector": fund.get("Sector") or None,
            "market_cap": fund.get("MarketCap") or None,
            "risk_level": rp["category"] if rp["risk_score"] is not None else fs["risk_level"],
            "beta": rp["beta"], "volatility": rp["volatility"], "max_drawdown": rp["max_drawdown"],
            "score": m["Score"],
            "score_v2": comp["final"] if comp else m["Score"],
            "valuation": decision_engine.valuation_score(fund),
            "sector_score": sec_score,
            "confidence": proprietary.confidence(m)["score"],
            "status_group": classify(m)["group"],
        })
    # Benchmark: S&P 500 returns.
    b = _returns(mkt_close) if mkt_close is not None else {}
    benchmark = {"daily": b.get("daily"), "ret_1m": b.get("m1"), "ret_ytd": b.get("ytd")}
    payload = portfolio.build_portfolio(positions, benchmark)
    # Portfolio-level risk: correlation matrix + weighted beta/vol + concentration.
    if not payload.get("empty"):
        betas = {p["ticker"]: p.get("beta") for p in positions}
        vols = {p["ticker"]: p.get("volatility") for p in positions}
        payload["correlation"] = risk_engine.correlation_pairs(closes_pf)
        payload["risk"] = risk_engine.portfolio_risk(
            payload["positions"], betas, vols, payload["exposures"]["sector"])
        # Decision engine (Part 3): actions, allocation targets, rebalancing.
        payload["decisions"] = decision_engine.portfolio_decisions(
            payload["positions"], sectors, regime_label,
            payload["risk"], payload["correlation"])
    return payload


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    tickers = load_watchlist(config.WATCHLIST_FILE)
    notifier = Notifier()
    print(f"נטענו {len(tickers)} מניות. מוריד נתונים חינמיים מ‑Yahoo Finance...\n")

    rows: list[dict] = []
    closes_map: dict[str, list] = {}   # symbol -> recent closes (for charts)
    backtest_rows: list[dict] = []     # historical signal performance per ticker
    events_map: dict[str, dict] = {}   # symbol -> earnings/analyst events
    backtest_map: dict[str, dict] = {}  # symbol -> institutional backtest stats
    failed_pulls = 0                    # tickers we couldn't get usable data for
    # Market history (for beta) fetched once.
    _mkt_df = load_ohlcv("^GSPC")
    mkt_close = _mkt_df["Close"] if _mkt_df is not None else None
    for sym in tickers:
        print(f"  · {sym} ...")
        price_df = load_ohlcv(sym)
        metrics = compute_indicators(price_df)
        if metrics is None:
            print(f"  ! {sym}: אין מספיק נתונים — דולג")
            failed_pulls += 1
            continue
        metrics["Ticker"] = sym
        metrics["Name"] = get_company_name(sym)   # English name (cached)
        metrics["Breakout"] = is_breakout(metrics)
        metrics["Score"] = score_stock(metrics)
        # Plain-Hebrew status + bottom line (shared engine).
        info = classify(metrics)
        metrics["Status"] = f"{info['emoji']} {info['label']}"
        metrics["Summary"] = info["summary"]
        if config.ENABLE_FUNDAMENTALS:
            metrics.update(get_fundamentals(sym))
        # Daily % change (last close vs previous close).
        close = price_df["Close"]
        metrics["DailyChange%"] = (round(float(close.iloc[-1] / close.iloc[-2] - 1) * 100, 2)
                                   if len(close) >= 2 else 0.0)
        # Keep ~60 recent closes for the sparkline charts.
        closes_map[sym] = close.tail(60).tolist()
        # Factor sub-scores (technical / fundamental / sentiment / risk).
        # News sentiment is fetched on demand in the dashboard (kept fast here).
        fs = factor_scores(metrics, closes=closes_map[sym], fundamentals=metrics)
        metrics["ScoreFundamental"] = fs["fundamental"]
        metrics["ScoreSentiment"] = fs["sentiment"]
        metrics["ScoreRisk"] = fs["risk"]
        metrics["RiskLevel"] = fs["risk_level"]
        # Risk Intelligence Engine (Part 2): beta / volatility / max drawdown.
        # Its risk score OVERRIDES the simple one and feeds the composite (v2).
        rp = risk_engine.risk_profile(price_df["Close"], mkt_close)
        metrics["Beta"] = rp["beta"]
        metrics["Volatility"] = rp["volatility"]
        metrics["MaxDrawdown"] = rp["max_drawdown"]
        metrics["RiskWarnings"] = " · ".join(rp["warnings"])
        # Support/Resistance levels (Phase 24) — real swing pivots + 52w extremes.
        srl = technicals.sr_levels(price_df)
        metrics["Support"] = srl["support"] if srl else None
        metrics["Resistance"] = srl["resistance"] if srl else None
        metrics["DistSupport%"] = srl["dist_support_pct"] if srl else None
        metrics["DistResistance%"] = srl["dist_resistance_pct"] if srl else None
        metrics["RiskReward"] = srl["risk_reward"] if srl else None
        if rp["risk_score"] is not None:
            metrics["ScoreRisk"] = rp["risk_score"]
            metrics["RiskLevel"] = rp["category"]
        # Per-stock news score (needed by the composite Final Score v2).
        metrics["ScoreNews"] = (score_headlines(get_headlines(sym, config.NEWS_LIMIT))["score"]
                                if config.ENABLE_NEWS else 50)
        rows.append(metrics)
        # Institutional backtest of the breakout signal (reuses price_df + market).
        bt = backtest_signal(price_df, mkt_close)
        if bt:
            backtest_map[sym] = bt
            backtest_rows.append({"Ticker": sym, "Name": metrics["Name"], **bt})
        # Proprietary per-stock estimates (real-data heuristics, clearly labeled).
        metrics["ExpectedUpside%"] = proprietary.expected_upside(metrics)["pct"]
        conf = proprietary.confidence(metrics, bt["win_rate"] if bt else None)
        metrics["Confidence"] = conf["score"]
        metrics["ConfidenceLevel"] = conf["level"]
        # Corporate events (earnings / analyst actions) for catalysts & alerts.
        if config.ENABLE_EVENTS:
            events_map[sym] = events_mod.get_events(sym)

    if not rows:
        raise SystemExit("לא התקבלו נתונים עבור אף מניה. יוצא.")

    df = pd.DataFrame(rows)

    # Market context fetched HERE (needed for each stock's Sector Score in the
    # composite, and reused by the market-overview section below).
    print("\nמושך נתוני שוק ומחשב מדדים קנייניים...")
    try:
        indices = market.get_indices()
        regime = market.market_regime_score()
        sectors = market.sector_intelligence()
    except Exception as exc:
        print(f"  ! נתוני שוק לא זמינים: {exc}")
        indices, regime, sectors = [], {"score": "-", "label": ""}, []

    # --- Composite Final Score v2 (Phase 14): Fundamental 35 / Technical 25 /
    #     Sector 20 / News 10 / Risk 10, with per-dimension contributions. ---
    v2, cF, cT, cS, cN, cR, comp = [], [], [], [], [], [], []
    for _, r in df.iterrows():
        ss = market.sector_score_for(r.get("Sector"), sectors)
        c = composite_score(technical=r["Score"], fundamental=r.get("ScoreFundamental"),
                            sector=ss, news=r.get("ScoreNews"), risk=r.get("ScoreRisk"))
        if c:
            k = c["contributions"]
            v2.append(c["final"]); comp.append(int(c["completeness"] * 100))
            cF.append(k.get("fundamental")); cT.append(k.get("technical"))
            cS.append(k.get("sector")); cN.append(k.get("news")); cR.append(k.get("risk"))
        else:
            v2.append(int(r["Score"])); comp.append(None)
            cF.append(None); cT.append(None); cS.append(None); cN.append(None); cR.append(None)
    df["ScoreV2"] = v2
    df["ContribFund"], df["ContribTech"], df["ContribSector"] = cF, cT, cS
    df["ContribNews"], df["ContribRisk"], df["Completeness"] = cN, cR, comp

    # --- Trust Score (Part 6): meta-confidence per recommendation ---
    ts_s, ts_c = [], []
    for _, r in df.iterrows():
        ti = trust_engine.trust_score(r, backtest_map.get(r["Ticker"]))
        ts_s.append(ti["score"]); ts_c.append(ti["category"])
    df["TrustScore"], df["TrustCategory"] = ts_s, ts_c

    base_cols = [
        "Ticker", "Name", "Status", "Summary", "Date", "Price", "DailyChange%",
        "ScoreV2", "TrustScore", "TrustCategory", "Score", "ScoreFundamental",
        "ScoreSentiment", "ScoreRisk", "ScoreNews",
        "ContribFund", "ContribTech", "ContribSector", "ContribNews", "ContribRisk", "Completeness",
        "MA20", "MA50", "MA200", "RSI14", "AvgVol20", "CurVol",
        "VolRatio", "High52w", "DistFromHigh%", "RiskLevel",
        "Beta", "Volatility", "MaxDrawdown", "RiskWarnings",
        "ExpectedUpside%", "Confidence", "ConfidenceLevel", "Breakout",
    ]
    extra = [c for c in df.columns if c not in base_cols]
    # Rank by the new composite Final Score v2.
    df = df[base_cols + extra].sort_values("ScoreV2", ascending=False).reset_index(drop=True)

    export(df)

    # Fire alerts for breakout candidates (console + file log).
    breakouts = df[df["Breakout"] == True]  # noqa: E712
    if len(breakouts):
        notifier.send(
            f"{len(breakouts)} מועמדים לפריצה: " + ", ".join(breakouts["Ticker"]),
            level="התראה",
        )
        # Attach a recent headline per candidate (cheap — few tickers).
        if config.ENABLE_NEWS:
            for t in breakouts["Ticker"]:
                heads = get_headlines(t, config.NEWS_LIMIT)
                if heads:
                    notifier.send(f"{t} — {heads[0]['title']}")

    # Email the full daily report. By default only on days with a breakout
    # candidate (avoids daily noise); set EMAIL_ALWAYS=True to send every run.
    if config.ENABLE_EMAIL and (len(breakouts) or config.EMAIL_ALWAYS):
        subject, html, text, images = build_report_email(df, closes_map)
        EmailNotifier().send(subject, html, text, images=images)

    # Market overview + proprietary indicators (reuse indices/regime/sectors
    # already fetched above for the composite) — saved to JSON for the dashboard.
    vix = next((ix["price"] for ix in indices if ix["name"] == "VIX"), None)
    breadth = proprietary.market_breadth(df)
    fng = proprietary.fear_greed(df, vix, breadth)
    flow = proprietary.capital_flow(sectors)
    try:
        spx_hist = market.get_index_history("^GSPC", "6mo")
        spx_hist = [round(float(x), 2) for x in spx_hist] if spx_hist is not None else []
    except Exception:
        spx_hist = []
    market_overview = {
        "date": datetime.now().strftime(config.DATE_FMT),
        "indices": indices, "regime": regime, "sectors": sectors,
        "breadth": breadth, "fear_greed": fng, "capital_flow": flow,
        "spx_hist": spx_hist,
    }
    # Alert Center (Phase 8) — typed alerts from real signals.
    alert_center = build_alerts(df, sectors, events_map)
    # AI Insights (Phase 11) — rule-based Hebrew briefing from the day's data.
    market_overview["insights"] = insights_mod.generate_insights(market_overview, df, alert_center)
    try:
        with open(config.MARKET_JSON, "w", encoding="utf-8") as fh:
            json.dump(market_overview, fh, ensure_ascii=False, indent=2)
        with open(config.CLOSES_JSON, "w", encoding="utf-8") as fh:
            json.dump({k: [round(float(x), 2) for x in v if x == x]
                       for k, v in closes_map.items()}, fh)
        with open(config.EVENTS_JSON, "w", encoding="utf-8") as fh:
            json.dump(events_map, fh, ensure_ascii=False)
        with open(config.ALERTS_CENTER_JSON, "w", encoding="utf-8") as fh:
            json.dump(alert_center, fh, ensure_ascii=False, indent=2)
        with open(config.BACKTEST_JSON, "w", encoding="utf-8") as fh:
            json.dump(backtest_map, fh, ensure_ascii=False, indent=2)
        # System health (Part 6) — pipeline-level metrics.
        sec_dist = (df["Sector"].dropna().value_counts().to_dict()
                    if "Sector" in df else {})
        system_health = {
            "scanned": len(df),
            "signals": int(df["Breakout"].sum()),
            "data_completeness": round(float(df["Completeness"].mean()), 1),
            "failed_pulls": failed_pulls,
            "avg_confidence": round(float(df["Confidence"].mean()), 1),
            "avg_trust": round(float(df["TrustScore"].mean()), 1),
            "sector_distribution": {str(k): int(v) for k, v in sec_dist.items()},
            "date": datetime.now().strftime(config.DATE_FMT),
        }
        with open(config.SYSTEM_HEALTH_JSON, "w", encoding="utf-8") as fh:
            json.dump(system_health, fh, ensure_ascii=False, indent=2)
        # Global market indicators (Phase 30) — crypto/FX/commodities/rates.
        import globalmkt
        with open(config.GLOBAL_JSON, "w", encoding="utf-8") as fh:
            json.dump(globalmkt.build(), fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"  ! שמירת artifact נכשלה: {exc}")

    # Portfolio analytics (Phase 7) — computed from portfolio.csv holdings.
    try:
        portfolio_payload = build_portfolio_payload(sectors=sectors,
                                                    regime_label=regime.get("label", ""))
        with open(config.PORTFOLIO_JSON, "w", encoding="utf-8") as fh:
            json.dump(portfolio_payload, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"  ! חישוב התיק נכשל: {exc}")

    # Write the full deliverable set (timestamped + latest + index.html).
    write_timestamped_outputs(df, closes_map, notifier.history, backtest_rows,
                              indices, regime)

    hebrew_summary(df)


if __name__ == "__main__":
    main()
