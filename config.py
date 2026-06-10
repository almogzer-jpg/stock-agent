# -*- coding: utf-8 -*-
"""Central configuration for the stock-agent package.

Every tunable threshold, file path, and feature flag lives here so the rest of
the package stays free of magic numbers. Edit this file to retune the agent.
"""
import os

# --- Paths ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_FILE = os.path.join(BASE_DIR, "watchlist.txt")
DATA_DIR = os.path.join(BASE_DIR, "data")            # outputs land here
os.makedirs(DATA_DIR, exist_ok=True)

RESULTS_CSV = os.path.join(DATA_DIR, "results.csv")     # "latest" pointer (dashboard reads this)
RESULTS_XLSX = os.path.join(DATA_DIR, "results.xlsx")
ALERTS_LOG = os.path.join(DATA_DIR, "alerts.log")

# Every run also writes a full, timestamped set of deliverables here, plus
# fixed-name "latest" copies (daily_report.html/.xlsx, opportunities.csv, alerts.csv).
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# Static, self-contained dashboard snapshot regenerated every run.
DASHBOARD_INDEX = os.path.join(BASE_DIR, "dashboard", "index.html")

# --- Data ----------------------------------------------------------------
# ~2y of daily candles so the 200-day MA / 52-week high are valid.
HISTORY_PERIOD = "2y"
DATE_FMT = "%d/%m/%Y"                                 # Israeli standard DD/MM/YYYY

# --- Breakout thresholds (scanners/breakout.py) --------------------------
NEAR_HIGH_PCT = 10.0      # within 10% of the 52-week high
VOLUME_SPIKE = 1.5        # current volume >= 1.5x the 20-day average
RSI_MIN = 50.0            # healthy-momentum RSI band, lower bound
RSI_MAX = 75.0            # healthy-momentum RSI band, upper bound

# --- Feature flags -------------------------------------------------------
# Fundamentals call yfinance's per-ticker .info, which is slower and can be
# rate-limited, so it's off by default. Flip to True to enrich the export.
ENABLE_FUNDAMENTALS = False
# News is fetched only for breakout candidates (few calls), so it's cheap.
ENABLE_NEWS = True
NEWS_LIMIT = 5

# Email an alert when breakout candidates appear. Credentials live in
# email_config.json (or env vars) — see alerts/email_notifier.py. If nothing
# is configured, sending is a safe no-op.
ENABLE_EMAIL = True
# Manual "refresh" from the dashboard sets STOCK_AGENT_DISABLE_EMAIL=1 so a
# button click never spams email; the scheduled daily run still emails.
if os.environ.get("STOCK_AGENT_DISABLE_EMAIL") == "1":
    ENABLE_EMAIL = False
# By default the report is emailed only on days with a breakout candidate.
# Set to True to receive the full report every run (e.g. every weekday).
EMAIL_ALWAYS = False
EMAIL_CONFIG_FILE = os.path.join(BASE_DIR, "email_config.json")

# --- Hebrew display labels -----------------------------------------------
# Internal metric keys stay English (used across modules); these Hebrew labels
# are applied only to user-facing output: the CSV/Excel headers and dashboard.
COLUMN_LABELS_HE = {
    "Ticker": "סימול",
    "Name": "שם",
    "Status": "סטטוס",
    "Summary": "שורה תחתונה",
    "Date": "תאריך",
    "Price": "מחיר",
    "MA20": "ממוצע 20",
    "MA50": "ממוצע 50",
    "MA200": "ממוצע 200",
    "RSI14": "RSI(14)",
    "DailyChange%": "שינוי יומי %",
    "RiskLevel": "רמת סיכון",
    "ScoreSentiment": "ציון סנטימנט",
    "ScoreRisk": "ציון סיכון",
    "ScoreFundamental": "ציון פונדמנטלי",
    "AvgVol20": "נפח ממוצע 20",
    "CurVol": "נפח נוכחי",
    "VolRatio": "יחס נפח",
    "High52w": "שיא 52 שבועות",
    "DistFromHigh%": "מרחק משיא %",
    "Breakout": "פריצה",
    "Score": "ציון",
    # Fundamentals (when enabled)
    "MarketCap": "שווי שוק",
    "TrailingPE": "מכפיל רווח",
    "ForwardPE": "מכפיל עתידי",
    "ProfitMargin": "שולי רווח",
    "RevenueGrowth": "צמיחת הכנסות",
    "Sector": "סקטור",
}
