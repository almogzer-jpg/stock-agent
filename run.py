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
from datetime import datetime

import pandas as pd

import config
from data_loader import load_ohlcv
from names import get_company_name
from indicators.technical import compute_indicators
from scanners.breakout import is_breakout
from ranking_engine.score import score_stock
from ranking_engine.interpret import classify
from ranking_engine.factor_scores import factor_scores
from charts import sparkline_png
from fundamentals.fundamentals import get_fundamentals
from news.headlines import get_headlines
from backtesting.backtester import backtest_symbol
import market
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
    "Ticker": "סימול", "Name": "שם", "signals": "מספר איתותים",
    "hit_rate": "אחוז הצלחה %", "avg_return_pct": "תשואה ממוצעת %",
    "horizon": "טווח (ימי מסחר)",
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
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    tickers = load_watchlist(config.WATCHLIST_FILE)
    notifier = Notifier()
    print(f"נטענו {len(tickers)} מניות. מוריד נתונים חינמיים מ‑Yahoo Finance...\n")

    rows: list[dict] = []
    closes_map: dict[str, list] = {}   # symbol -> recent closes (for charts)
    backtest_rows: list[dict] = []     # historical signal performance per ticker
    for sym in tickers:
        print(f"  · {sym} ...")
        price_df = load_ohlcv(sym)
        metrics = compute_indicators(price_df)
        if metrics is None:
            print(f"  ! {sym}: אין מספיק נתונים — דולג")
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
        rows.append(metrics)
        # Backtest the breakout signal on this ticker's history (reuses price_df).
        bt = backtest_symbol(price_df)
        if bt:
            backtest_rows.append({"Ticker": sym, "Name": metrics["Name"], **bt})

    if not rows:
        raise SystemExit("לא התקבלו נתונים עבור אף מניה. יוצא.")

    # Build results, score-ranked. Keep the core columns first; any
    # fundamentals columns (when enabled) follow.
    df = pd.DataFrame(rows)
    base_cols = [
        "Ticker", "Name", "Status", "Summary", "Date", "Price", "DailyChange%",
        "MA20", "MA50", "MA200", "RSI14", "AvgVol20", "CurVol",
        "VolRatio", "High52w", "DistFromHigh%", "RiskLevel",
        "ScoreSentiment", "ScoreRisk", "ScoreFundamental", "Breakout", "Score",
    ]
    extra = [c for c in df.columns if c not in base_cols]
    df = df[base_cols + extra].sort_values("Score", ascending=False).reset_index(drop=True)

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

    # Market context for the dashboard snapshot (real index data; best-effort).
    print("\nמושך נתוני מדדים ומצב שוק...")
    try:
        indices = market.get_indices()
        regime = market.market_regime_score()
    except Exception as exc:
        print(f"  ! נתוני שוק לא זמינים: {exc}")
        indices, regime = [], {"score": "-", "label": ""}

    # Write the full deliverable set (timestamped + latest + index.html).
    write_timestamped_outputs(df, closes_map, notifier.history, backtest_rows,
                              indices, regime)

    hebrew_summary(df)


if __name__ == "__main__":
    main()
