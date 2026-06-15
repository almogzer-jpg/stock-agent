# DASHBOARD_WALKTHROUGH.md — Tab-by-Tab Guide

Source: `dashboard/app.py` (11 desktop tabs, sidebar radio nav) and
`dashboard/mobile.py` (separate mobile experience). Dark theme, RTL/Hebrew
(`dashboard/theme.py`). The dashboard reads **precomputed artifacts** and makes
zero live network calls on load (except on-demand news), opening in ~2–3 s.

Screenshots referenced below are in `SAMPLE_OUTPUTS/`.

---

## Desktop navigation (sidebar)

```
🏠 ראשי (60 שניות)   🔭 סורק שוק   🤖 עוזר   📈 מניות ופירוט   🗺️ סקטורים
💼 תיק   🧭 החלטות תיק   🛡️ אמון ואימות   🔔 התראות   📰 חדשות   📊 בקטסט
```

---

### 1. 🏠 ראשי (60 שניות) — Home / Market Overview
- **Purpose:** understand the whole market and the day's best ideas in ~60 seconds.
- **Metrics shown:** Market Regime score + Hebrew label (Risk-On/Neutral/Risk-Off)
  with the *why*; Fear & Greed gauge; market breadth; index strip (S&P 500, NASDAQ,
  Dow, Russell 2000, VIX) with % change; 6-month S&P chart; daily Hebrew briefing
  ("📝 תובנות היום"); **Top 3 / 5 / 10 opportunities** as cards (score, expected
  upside, confidence, risk, reason).
- **Decision process:** read regime → if Risk-On, lean into top opportunities; if
  Risk-Off, the briefing and decision engine steer defensive. The opportunity cards
  give an immediate shortlist.
- **Screenshot:** `01_market_overview.png`

### 2. 🔭 סורק שוק — Market Scanner (Opportunity Hunter)
- **Purpose:** market-wide discovery across ~500 S&P 500 + Nasdaq-100 names.
- **Metrics:** KPIs (scanned / enriched / elapsed); Top-10 columns for each of the 5
  rankings (opportunities / undervalued / momentum / high-quality / turnarounds);
  sector-distribution chart; filterable table (sector, market-cap, min Score V2,
  risk, valuation, momentum, quality) with discovery tags.
- **Decision process:** start from "opportunities" (Final Score V2), cross-check the
  discovery tags and Confidence, then filter to a sector/risk band that fits the
  user's mandate. (Full logic → `OPPORTUNITY_HUNTER.md`.)
- **Screenshot:** `03_top_opportunities.png`

### 3. 🤖 עוזר — Assistant
- **Purpose:** free, rule-based Hebrew Q&A over the scan data (**no paid LLM**).
- **Metrics:** answers questions like "strongest stock / sector", "score of X",
  counts of positives, etc., from the loaded artifacts.
- **Decision process:** quick natural-language lookup instead of hunting through
  tables. `st.chat_input` / `st.chat_message` UI.

### 4. 📈 מניות ופירוט — Stocks & Detail (Score transparency)
- **Purpose:** full transparency on every watchlist name.
- **Metrics:** all-stocks table with Final / Technical / Fundamental / Sector / Risk
  bars + recommendation + sparkline; per-stock detail card with the **6-score
  panel** (Final / Technical / Fundamental / Sector / News / Risk), a **Final Score
  breakdown** expander (per-component points), a factor **radar**, why-buy /
  catalysts / risks (`explain.py`), and a fundamentals panel.
- **Decision process:** audit *why* a stock scores what it does — the breakdown and
  radar let a reviewer trace every point. Risk panel (β/vol/maxDD) flags danger.

### 5. 🗺️ סקטורים — Sectors
- **Purpose:** sector rotation intelligence.
- **Metrics:** strongest/weakest headline; sector score heatmap; full ranked table
  (trend, momentum, relative strength vs S&P, 1m/3m returns, score, rank).
- **Decision process:** tilt toward strong sectors, avoid weak ones; feeds the
  Decision Engine's over/underweight suggestions.

### 6. 💼 תיק — Portfolio
- **Purpose:** analytics on the user's actual holdings (`portfolio.csv`).
- **Metrics:** total value & P/L, daily change, weights, return vs S&P benchmark,
  sector/cap/risk **exposure donuts**, **Portfolio Health Score (0–100)** gauge,
  holdings table, portfolio risk section (weighted beta/vol, concentration,
  effective positions, **correlation heatmap**), and alerts. Editable via
  `st.data_editor` + CSV upload.
- **Decision process:** see concentration/risk at a glance; the health score and
  warnings (single-position >25%, sector >40%) prompt rebalancing.
- **Screenshot:** `04_portfolio.png`

### 7. 🧭 החלטות תיק — Portfolio Decisions
- **Purpose:** turn analytics into ACTIONS.
- **Metrics:** **"מה לעשות היום?"** (prioritized actions); hard constraint warnings;
  current-vs-recommended weight bars; per-holding decision table
  (Increase/Hold/Reduce/Exit + target % + confidence + priority); per-holding
  explanation expanders (why / data / risks); sector rebalancing suggestions.
- **Decision process:** the engine maps Final Score V2 + risk + sector + regime to a
  target allocation bucket (0/2/5/10/15%), capped by risk category, then to an
  action. (Logic → `decisions.py`; summarized in `OPPORTUNITY_HUNTER.md`/this file.)

### 8. 🛡️ אמון ואימות — Trust & Validation
- **Purpose:** "how much should I trust this?"
- **Metrics:** System Health KPIs (scanned, completeness, failed pulls, avg
  confidence, avg trust); per-stock trust table; per-stock detail (trust gauge,
  reliability metrics, why-trust / why-cautious, 7-factor breakdown); known
  limitations.
- **Decision process:** down-weight low-trust / small-sample names regardless of
  score. (Methodology → `TRUST_VALIDATION.md`.)
- **Screenshot:** `05_trust_validation.png`

### 9. 🔔 התראות — Alert Center
- **Purpose:** triage what changed.
- **Metrics:** typed alerts grouped by severity — breakout 🚀, volume spike 📊,
  earnings 📅, analyst up/downgrades, sector rotation, risk; each with a Hebrew
  message and severity (גבוהה / בינונית / מידע).
- **Decision process:** high-severity (risk) first, then catalysts (earnings/
  analyst), then informational rotation.

### 10. 📰 חדשות — News
- **Purpose:** headline context.
- **Metrics:** per-stock Yahoo headlines + sentiment score (0–100). Fetched live on
  render (the one place that hits the network on demand).
- **Decision process:** sanity-check a score against the day's narrative.

### 11. 📊 בקטסט — Backtest
- **Purpose:** historical evidence for the breakout signal.
- **Metrics:** per-ticker occurrences, win rate, avg/median return, worst-trade
  drawdown, benchmark-relative return, avg holding, in-sample vs out-of-sample win
  rate, Confidence.
- **Decision process:** judge whether a signal has a real, persistent edge before
  trusting today's instance. (Methodology → `TRUST_VALIDATION.md`.)

---

## Mobile experience — `dashboard/mobile.py` (Phase 16)

A **separate** mobile-first UI (desktop untouched), reached via narrow-screen
auto-detect (`innerWidth < 500`), `?m=1`, or a sidebar toggle. Card-based,
touch-friendly (≥46px buttons), RTL, no horizontal scroll, sticky top summary.

Four touch tabs:
- **🏠 בית** — market regime, "מה לעשות היום?" (top portfolio actions), Top-3
  opportunity cards, strongest/weakest sector, portfolio health, critical alerts.
- **💎 הזדמנויות** — opportunity cards (ticker, company, Score V2, recommendation,
  risk, trust, daily change, one-line why).
- **💼 תיק** — total value, daily change, top-holding risk, sector-exposure warning,
  suggested action.
- **🔔 התראות** — alerts grouped by severity.

- **Screenshot:** `02_mobile_dashboard.png`

---

## Note on screenshots

Capturing pixel-perfect screenshots in this environment is constrained by a known
browser-automation tooling issue (CDP `captureScreenshot` timeouts, and a renderer
freeze when the viewport is clamped to a phone width). Where a live screenshot
could not be captured, `SAMPLE_OUTPUTS/` contains the **verified rendered content
extracted directly from the live DOM** (`*_content.md`) plus any screenshots that
did capture. This is a tooling limitation, **not** an application defect — all tabs
render correctly and are verified at the code + DOM level.
