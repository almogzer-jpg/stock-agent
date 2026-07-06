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

# Precomputed artifacts so the dashboard loads instantly (zero live calls).
MARKET_JSON = os.path.join(DATA_DIR, "market_overview.json")   # market + proprietary indicators
CLOSES_JSON = os.path.join(DATA_DIR, "closes.json")            # recent closes per ticker (charts)
EVENTS_JSON = os.path.join(DATA_DIR, "events.json")            # earnings/analyst events per ticker
ALERTS_CENTER_JSON = os.path.join(DATA_DIR, "alerts_center.json")  # typed alerts (Alert Center)
BACKTEST_JSON = os.path.join(DATA_DIR, "backtest.json")        # per-ticker signal backtest stats
UNIVERSE_JSON = os.path.join(DATA_DIR, "universe.json")        # market-wide scan results (Market Scanner)
SYSTEM_HEALTH_JSON = os.path.join(DATA_DIR, "system_health.json")  # pipeline health metrics
GLOBAL_JSON = os.path.join(DATA_DIR, "global_markets.json")        # global macro/crypto/FX indicators

# Market Scanner (Part 5): which index universe + how many top names to deeply enrich.
SCAN_UNIVERSE = "ALL"          # SP500 / NASDAQ100 / ALL
SCAN_TOP_ENRICH = 40           # deep-enrich (fundamentals/composite/backtest) only the top-N

# Fetch corporate events (earnings dates, analyst actions) for catalysts/alerts.
# Adds per-ticker yfinance calls — slower; turn off to speed up if needed.
ENABLE_EVENTS = True

# Portfolio (Phase 7): holdings you edit, analytics computed into JSON.
PORTFOLIO_CSV = os.path.join(BASE_DIR, "portfolio.csv")
PORTFOLIO_JSON = os.path.join(DATA_DIR, "portfolio.json")

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
# Fundamentals (Revenue/EPS/FCF growth, margins, D/E, ROIC, PEG, fwd PE).
# Cached weekly (they change quarterly) so daily runs stay fast.
ENABLE_FUNDAMENTALS = True
FUNDAMENTALS_CACHE = os.path.join(DATA_DIR, "fundamentals_cache.json")
FUNDAMENTALS_TTL_DAYS = 7
# News is fetched only for breakout candidates (few calls), so it's cheap.
ENABLE_NEWS = True
NEWS_LIMIT = 5

# Email an alert when breakout candidates appear. Credentials live in
# email_config.json (or env vars) — see alerts/email_notifier.py. If nothing
# is configured, sending is a safe no-op.
# DISABLED by user request — no daily email is sent. Set back to True to re-enable.
ENABLE_EMAIL = False
# Manual "refresh" from the dashboard sets STOCK_AGENT_DISABLE_EMAIL=1 so a
# button click never spams email; the scheduled daily run still emails.
if os.environ.get("STOCK_AGENT_DISABLE_EMAIL") == "1":
    ENABLE_EMAIL = False
# Email the full report on EVERY run (every weekday morning), not only on
# days with a breakout candidate.
EMAIL_ALWAYS = True
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
    "Beta": "ביתא",
    "Volatility": "תנודתיות %",
    "MaxDrawdown": "ירידה מקס׳ %",
    "RiskWarnings": "אזהרות סיכון",
    "ScoreSentiment": "ציון סנטימנט",
    "ScoreRisk": "ציון סיכון",
    "ScoreFundamental": "ציון פונדמנטלי",
    "ExpectedUpside%": "פוטנציאל עלייה %",
    "Confidence": "ביטחון %",
    "ConfidenceLevel": "רמת ביטחון",
    "ScoreNews": "ציון חדשות",
    "ScoreV2": "ציון סופי v2",
    "TrustScore": "ציון אמון",
    "TrustCategory": "רמת אמון",
    "ContribFund": "תרומת פונדמנטלי",
    "ContribTech": "תרומת טכני",
    "ContribSector": "תרומת סקטור",
    "ContribNews": "תרומת חדשות",
    "ContribRisk": "תרומת סיכון",
    "Completeness": "שלמות נתונים",
    "AvgVol20": "נפח ממוצע 20",
    "CurVol": "נפח נוכחי",
    "VolRatio": "יחס נפח",
    "High52w": "שיא 52 שבועות",
    "DistFromHigh%": "מרחק משיא %",
    # Support/Resistance (Phase 24)
    "Support": "תמיכה",
    "Resistance": "התנגדות",
    "DistSupport%": "מרחק מתמיכה %",
    "DistResistance%": "מרחק מהתנגדות %",
    "RiskReward": "סיכון/סיכוי",
    "Breakout": "פריצה",
    "Score": "ציון",
    # Fundamentals
    "Sector": "סקטור",
    "MarketCap": "שווי שוק",
    "RevenueGrowth": "צמיחת הכנסות %",
    "EPSGrowth": "צמיחת רווח למניה %",
    "FCFGrowth": "צמיחת תזרים חופשי %",
    "OperatingMargin": "שולי תפעול %",
    "DebtToEquity": "חוב/הון",
    "ROIC": "ROIC %",
    "PEG": "PEG",
    "ForwardPE": "מכפיל עתידי",
}
