# Stock Agent Pro — System Review

> Technical & product review for a senior engineer onboarding to the platform.
> Repo: `C:\claude\stock-agent` · ~4,100 LOC Python · UI: Streamlit (Hebrew/RTL).
> Reviewed: June 2026.

---

## 1. Executive Summary

**What it is.** A free, single-user investment-intelligence platform that scans a
watchlist of US equities daily, scores and ranks them, analyzes sectors, tracks a
personal portfolio, generates typed alerts and a Hebrew daily briefing, and serves
it all through a dark, RTL Streamlit dashboard. It also emails a daily report.

**Main purpose.** Compress the morning research routine into ~60 seconds: *what is
the market doing, what are today's best opportunities and why, what are the risks,
and how is my portfolio positioned.*

**Cost / data.** 100% free — all data from `yfinance` (Yahoo Finance). No paid APIs.

**Maturity level.** **Late MVP / early production** for personal use. All 11
originally-planned phases are implemented and validated. The engineering is solid
(automated tests, precomputed artifacts, data-quality guards). The *investment
methodology* is intermediate: strong technical/momentum + sector RS, real
fundamentals, but no risk-model, correlation, or position-sizing layer.

**Production readiness.** **Engineering readiness ≈ 92/100** (works reliably, tested,
fast). **Investment-product readiness ≈ 83/100** (decision depth is the gap, see §12
and §14). Suitable as a *monitoring & screening* tool; **not** a turnkey
decision/execution engine for real capital.

---

## 2. Architecture

### 2.1 Folder structure
```
stock-agent/
├── run.py                  # daily orchestrator (entry point)
├── config.py               # all paths, thresholds, flags, Hebrew labels
├── data_loader.py          # shared yfinance OHLCV loader (NaN-safe)
├── names.py                # company-name resolver (cached)
├── market.py               # indices, sector intelligence, regime, sector mapping
├── charts.py               # matplotlib sparklines (email/report)
├── proprietary.py          # calculated indicators (fear&greed, breadth, flow, upside, confidence)
├── events.py               # earnings dates + analyst actions (yfinance, best-effort)
├── explain.py              # why-buy/watch/avoid + catalysts + risks (rule-based)
├── insights.py             # daily Hebrew AI briefing (rule-based NLG)
├── portfolio.py            # portfolio analytics
├── assistant.py            # free rule-based Q&A over the scan
├── indicators/technical.py # MAs, RSI, volume, 52w metrics
├── scanners/breakout.py    # breakout setup detector
├── ranking_engine/
│   ├── score.py            # 0-100 final score + transparent breakdown
│   ├── factor_scores.py    # technical/fundamental/sentiment/risk sub-scores
│   └── interpret.py        # group (positive/watch/avoid) + plain-Hebrew text
├── fundamentals/fundamentals.py  # 8 fundamental metrics (weekly cache)
├── backtesting/backtester.py     # forward-return test of the breakout signal
├── news/{headlines,sentiment}.py # free headlines + keyword sentiment
├── alerts/{notifier,email_notifier,center}.py  # console/log, email, typed alert center
├── dashboard/{app.py,theme.py}   # Streamlit UI + dark theme; index.html generated
├── tests/                  # pytest suite (8 files, 48 tests)
├── data/                   # generated: results.csv/.xlsx, *.json artifacts, logs
│   └── outputs/            # timestamped + "latest" deliverables per run
├── watchlist.txt           # tickers (one per line)
├── portfolio.csv           # holdings: Ticker, Quantity, AverageCost
├── run_daily.bat           # Task Scheduler wrapper (Mon–Fri 09:00)
└── dashboard.bat           # one-click launcher (+ desktop shortcut)
```

### 2.2 Data flow (one-way pipeline)
```
watchlist.txt
     │
     ▼
data_loader (yfinance OHLCV) ──► indicators ──► scanners.breakout
     │                                      └──► ranking_engine.score / interpret
     │                                      └──► ranking_engine.factor_scores
     │                                      └──► backtesting
     │                                      └──► fundamentals (weekly cache)
     │                                      └──► events (earnings/analyst)
     ▼
run.py (orchestrator)
     ├─ market.py        → indices, sector_intelligence, regime
     ├─ proprietary.py   → fear&greed, breadth, capital flow, upside, confidence
     ├─ portfolio.py     → portfolio analytics (from portfolio.csv)
     ├─ alerts/center.py → typed alerts
     ├─ insights.py      → Hebrew daily briefing
     └─ WRITES ARTIFACTS:
          data/results.csv/.xlsx, market_overview.json, closes.json,
          events.json, alerts_center.json, portfolio.json,
          fundamentals_cache.json, dashboard/index.html, data/outputs/*
     │
     ├─ alerts/email_notifier → daily email (Gmail SMTP)
     ▼
dashboard/app.py  ──reads artifacts (ZERO live calls; news fetched on-demand only)
```

**Key architectural decision.** `run.py` precomputes everything into JSON/CSV
artifacts; the dashboard only *reads* them. Result: dashboard loads in ~2s with no
network calls. This fixed the original slowness/timeout problem and decouples the
(slow, network-bound) compute from the (instant) presentation layer.

### 2.3 Module dependencies (high level)
- `config` is imported by nearly everything (paths, thresholds, labels).
- `ranking_engine.factor_scores` depends on `ranking_engine.score`.
- `run.py` depends on almost all engines (orchestrator).
- `dashboard/app.py` depends on engines for *interpretation* (classify, factor_scores,
  explain, score_breakdown, sector mapping) but reads *data* from artifacts.
- Network-touching modules: `data_loader`, `market`, `events`, `fundamentals`,
  `names`, `news.headlines`. All others are pure functions (and unit-tested).

---

## 3. Data Sources

| Source | Data collected | Update freq | Reliability | Limitations |
|---|---|---|---|---|
| **yfinance — OHLCV** (`.history`) | Daily open/high/low/close/volume, split/div-adjusted | Per run (daily) | High | Latest candle may be partial intraday; occasional NaN rows (dropped in loader) |
| **yfinance — `.info`** | Sector, market cap, revenue/earnings growth, operating margin, debt/equity, forward PE, PEG | Weekly (cached) | Medium | Slow; fields frequently missing/stale; not point-in-time |
| **yfinance — statements** (`.cashflow`, `.financials`, `.balance_sheet`) | FCF growth, ROIC (derived) | Weekly (cached) | Low–Medium | Row names vary by version; banks/financials often N/A; noisy YoY |
| **yfinance — `.calendar` / `.get_earnings_dates`** | Next earnings date | Daily | Medium | Sometimes empty/late |
| **yfinance — `.upgrades_downgrades`** | Recent analyst rating actions | Daily | Low–Medium | Often sparse; firm/grade formatting varies |
| **yfinance — `.news`** | Recent headlines | On-demand (dashboard) | Medium | Schema changed across versions (handled defensively); no full article |
| **Index ETFs/symbols** `^GSPC ^IXIC ^DJI ^RUT ^VIX` | Index levels + daily change | Per run | High | — |
| **Sector SPDR ETFs** (XLK, XLF, XLV, …, XLC) | Sector price history (RS/momentum/trend) | Per run (batched `yf.download`) | High | ETF is a proxy for the sector, not the cap-weighted index itself |

**Single-source risk:** everything depends on Yahoo Finance. A Yahoo outage or
schema change degrades the whole system. There is no secondary/fallback provider.

---

## 4. Scoring Engine

All scores are 0–100. The **Final Score** drives ranking; the other four are
independent "lenses" displayed alongside it (they do **not** currently feed the
Final Score — an intentional, documented design choice, and a key limitation).

### 4.1 Final / Technical Score  (`ranking_engine/score.py`)
Sum of five raw components (weights sum to 100), clamped 0–100:

| Component | Weight | Rule |
|---|---|---|
| Trend structure | 25 | +8 price>MA50, +9 price>MA200, +8 MA50>MA200 |
| Proximity to 52w high | 20 | `max(0, 20·(1 − DistFromHigh%/20))` (0% away→20, ≥20%→0) |
| RSI momentum | 20 | 20 if 50–75; 10 if 40–50; 8 if 75–80; else 0 |
| Volume confirmation | 20 | 20 if VolRatio≥1.5; else `20·(VolRatio−1)/0.5` if ≥1.0; else 0 |
| Short-term posture | 15 | 15 if price>MA20 |

`score_breakdown()` exposes the raw per-component points for full transparency in
the UI. (Note: Technical Score ≡ Final Score by design.)

### 4.2 Fundamental Score  (`factor_scores.fundamental_score`)
Base 50, additive bands from real fundamentals; clamp 0–100. Returns `None` if no
fundamental fields are available (UI shows "אין נתון").

| Metric | + / − points |
|---|---|
| Revenue Growth | +8 (≥15%), +4 (≥5%), −8 (<0) |
| EPS Growth | +8 (≥15%), +4 (≥0%), −8 (<0) |
| FCF Growth | +5 (≥10%), 0 (≥0%), −5 (<0) |
| Operating Margin | +8 (≥20%), +4 (≥10%), −6 (<0) |
| Debt/Equity | +6 (≤0.5), +3 (≤1.0), −6 (>2.0) |
| ROIC | +10 (≥15%), +5 (≥8%), −5 (<0) |
| PEG | +8 (≤1), +4 (≤2), −6 (>2) |
| Forward PE | +4 (≤20), 0 (≤35), −6 (>35) |

### 4.3 Sector Score
Per-stock sector score = the score of the stock's sector (mapped EN→HE) from the
Sector Intelligence engine (§5). `None` if sector unknown.

### 4.4 News Score  (`news/sentiment.py`)
Transparent keyword lexicon over recent headlines:
`score = 100·pos/(pos+neg)`; **50 = neutral / no news**. Not deep NLP.

### 4.5 Risk Score  (`factor_scores.risk_score`) — higher = riskier
- Base from **annualized volatility** of ~60 recent closes: `clamp((vol%−15)/(60−15)·100)`
- +15 if RSI ≥ 75 (overbought), +15 if price < MA200, +10 if DistFromHigh% > 25
- `RiskLevel`: <33 נמוך (low) · <66 בינוני (med) · else גבוה (high)

### 4.6 Two proprietary per-stock estimates (clearly labeled "מדד קנייני")
- **Expected Upside %** = `DistFromHigh% · (0.4 + 0.6·Score/100)`; if already at the
  high (<3%), floor with a volatility term (`Risk/100·12`); clamp 0–60. A heuristic,
  **not a forecast**.
- **Confidence (0–100)** = bullish-factor count (40%) + technical/sentiment agreement
  (25%) + data quality / fundamentals present (15%) + backtest hit-rate (20%).

---

## 5. Sector Intelligence  (`market.sector_intelligence`)

One batched `yf.download` of 11 sector SPDR ETFs + `^GSPC` (1y). Per sector:

- **Trend** (vs MAs): price>MA50>MA200 → "עולה" (40 pts); price>MA50 → "מתחזק" (25);
  price<MA50<MA200 → "יורד" (0); else "מעורב" (15).
- **Momentum (0–100)**: `clamp((ret_1m% + 10)/25 · 100)` (−10%→0, +15%→100). Contributes
  `momentum/100 · 30`.
- **Relative Strength** vs S&P: `rs_1m = sector_ret_1m − spx_ret_1m`. Contributes
  `clamp((rs_1m + 8)/16 · 30, 0, 30)`.
- **Sector Score (0–100)** = trend_pts + momentum_pts + rs_pts; ranked desc (rank 1 = strongest).
- **Capital flow** (`proprietary.capital_flow`): ranks sectors by Sector Score →
  top 5 = estimated inflows, bottom 5 = outflows. Estimate, not actual fund-flow data.

---

## 6. Opportunity Hunter

**Screening** (`scanners.breakout.is_breakout`) — a stock is a *breakout candidate*
iff ALL hold: price>MA50 AND price>MA200 AND within 10% of 52w high AND VolRatio≥1.5
AND 50≤RSI≤75.

**Grouping** (`ranking_engine.interpret.classify`):
- 🟢 *positive* — breakout, OR (price>MA200 AND price>MA50 AND Score≥65)
- 🔴 *avoid* — price<MA200 OR RSI<40 OR Score<35
- 🟡 *watch* — everything else

**Ranking** — `positive` group sorted by Final Score → Top 3 / 5 / 10.

**Identification process per opportunity** — `explain.explain()` produces Why-Buy /
Why-Watch / Why-Avoid bullet lists + Key Catalysts + Key Risks, all rule-mapped to
real signals (MAs, RSI, volume, distance-to-high, fundamentals, events, sector).
Every positive opportunity is guaranteed to be above its 200-day MA or a breakout.

**Scope limitation:** the "hunter" only searches the ~20-name watchlist — it is not a
broad-universe scanner.

---

## 7. Portfolio Management  (`portfolio.py`, holdings in `portfolio.csv`)

**Per position:** Market Value = qty·price; Cost = qty·avg_cost; P/L = MV−Cost;
P/L% = price/avg_cost−1; Weight = MV/Total MV.

**Portfolio metrics:** Total Value, Total Cost, Total P/L (%), weighted Daily /
Monthly (1m) / YTD returns, and **benchmark comparison vs S&P 500** (daily/1m/YTD).

**Exposure** (weight % grouped): by **Sector**, by **Market-Cap bucket**
(Large ≥$10B / Mid $2–10B / Small <$2B), by **Risk Level**.

**Risk** is positional (each holding's RiskLevel) aggregated into exposure %.

**Portfolio Health Score (0–100):**
- Diversification (30): from effective positions `1/HHI` (Herfindahl), 1→0, 8+→30
- Sector concentration (25): max sector weight, ≤25%→25, ≥60%→0
- Risk concentration (25): % in high-risk holdings, 0%→25, ≥60%→0
- Position sizing (20): largest single position, ≤20%→20, ≥40%→0

**Import:** edit `portfolio.csv` (or in-dashboard `data_editor` / CSV upload).
*Current `portfolio.csv` holds SAMPLE holdings — replace with real ones.*

---

## 8. Alert Center  (`alerts/center.py`)

| Type | Trigger | Severity |
|---|---|---|
| פריצה (Breakout) | `is_breakout` true | גבוהה |
| זינוק נפח (Volume spike) | VolRatio ≥ 2.0 | בינונית |
| דוחות (Earnings) | earnings date ≤ 7 days away | בינונית |
| שינוי דירוג (Analyst) | recent upgrade/downgrade (≤14d) | גבוהה if downgrade, else מידע |
| אזהרת סיכון (Risk) | RiskLevel = high AND price < MA200 | גבוהה |
| רוטציית סקטורים (Sector rotation) | strongest sector score ≥70 (in) / weakest <35 (out) | מידע |

Alerts are sorted by severity (גבוהה → בינונית → מידע) and rendered color-coded.
Earnings/analyst data is best-effort from yfinance (often partial).

---

## 9. AI Insights  (`insights.py`) — rule-based (no paid LLM)

**Logic:** deterministic Hebrew natural-language generation from the day's computed
data. Chosen over a paid LLM to keep the system free and reproducible.

**Inputs:** `market_overview` (regime, fear&greed, breadth, indices, sectors), the
scan DataFrame (groups via `classify`), and `alerts_center`.

**Output (4 sections + 1-line summary):**
1. **Market** — regime label/score, fear&greed, breadth, index moves.
2. **Opportunities** — count of positives + top 3 with score & expected upside.
3. **Risks** — count of avoids + count of genuine risk alerts + the most-severe one
   (positive breakouts are excluded from "risks").
4. **Rotation** — strongest sector (in) / weakest sector (out) with scores & RS.

Rendered as the "📝 תובנות היום" card atop the home page. Every sentence maps to a
number shown elsewhere — no black box.

---

## 10. Dashboard  (`dashboard/app.py`) — Streamlit, dark theme, RTL

Loads precomputed artifacts (instant). Sidebar radio = 8 tabs. *(Live screenshots
captured during this review for: Home, Stocks, Sectors, Portfolio, Alerts, Backtest.)*

| Tab | Purpose | Data shown | User actions |
|---|---|---|---|
| 🏠 **ראשי (60s)** | Morning snapshot | AI briefing, market regime + WHY, fear&greed gauge, indices, S&P trend, KPI cards, Top 3/5/10 opportunity cards | Read; switch Top-N tabs |
| 🤖 **עוזר** | Free Q&A | Chat answers from scan data (strongest stock/sector, score of X, counts) | Type Hebrew questions |
| 📈 **מניות ופירוט** | Score transparency + detail | All-stocks table (Final/Technical/Fundamental/Sector/Risk bars + recommendation + sparkline); stock card with 6-score panel, score-breakdown expander, factor radar, why/catalysts/risks, fundamentals panel | Select a stock |
| 🗺️ **סקטורים** | Sector intelligence | Strongest/weakest headline, score heatmap, full ranked table (trend/momentum/RS/returns) | Read |
| 💼 **תיק** | Portfolio | KPIs vs S&P, exposure donuts (sector/risk/cap), health gauge, holdings table, portfolio alerts | Edit holdings (data_editor), upload CSV, "save & run" |
| 🔔 **התראות** | Alert center | Typed alerts grouped/colored by severity | Read |
| 📰 **חדשות** | News | Per-stock headlines + sentiment score (fetched live on render) | Read |
| 📊 **בקטסט** | Signal validation | Breakout hit-rate / avg forward return per stock | Read |

Plus a sidebar **"🔄 רענן נתונים"** button (re-runs the scan; no email) and a
**static `dashboard/index.html`** snapshot regenerated each run.

---

## 11. Testing & Validation

**Automated tests:** `tests/` — 8 files, **48 tests, 100% passing** (pure, no network,
~2s). Cover scoring/breakdown/classification, factor sub-scores, proprietary
indicators, portfolio math, alert generation, opportunity explanations, indicators,
sector mapping, sentiment.

**Coverage (pure logic):**
| Module | Cover |
|---|---|
| alerts/center, indicators/technical, scanners/breakout | 100% |
| ranking_engine/score, factor_scores | 97% |
| news/sentiment | 94% |
| proprietary | 93% |
| ranking_engine/interpret | 91% |
| explain | 85% |
| portfolio | 75% |
| market, events, fundamentals, *_notifier, headlines | low (network/IO — covered by E2E) |
| **Total (measured modules)** | **~64%** |

**End-to-end:** full `run.py` workflow → 18–22s, exit 0, all 14 artifacts produced,
no NaN (except correctly-N/A bank fields). Dashboard boots ~2–3s, all 8 tabs handled.

**Known gaps:** no unit tests for network/IO modules; no integration test that mocks
yfinance; no CI; no performance regression test; UI verified manually (browser
screenshot tooling was intermittently unstable — CDP timeouts).

---

## 12. Known Weaknesses (brutally honest)

**Methodology / decision quality**
1. **Final Score is momentum-only.** Fundamentals, sector, news and risk are shown
   but do NOT influence the ranking or the Buy/Watch/Avoid label. The headline call
   chases what already rose and flags quality-on-dip as "avoid".
2. **No risk model.** No correlation between holdings, no volatility-adjusted position
   sizing, no portfolio VaR/drawdown, no stops, no rebalancing logic. Health score is
   descriptive, not prescriptive.
3. **"Expected Upside" & "Confidence" are heuristics dressed as quant outputs** — they
   can create false precision.
4. **Backtest is shallow:** single signal, tiny samples (0–8 signals/stock), 10-day
   horizon, no transaction costs, no out-of-sample, no benchmark-relative stats.

**Data**
5. **Single free source (Yahoo).** No fallback; schema changes/outages break things.
6. **Fundamentals are flaky/derived:** FCF growth & ROIC computed from statements,
   often N/A (esp. financials/banks), not point-in-time (look-ahead risk in any
   historical use).
7. **News sentiment is a naive keyword lexicon** (English), easily fooled.

**Scope / product**
8. **Tiny static universe (~20 mega-cap, tech-heavy).** Itself a concentrated,
   correlated bet; no bonds/income/international/small-cap/value.
9. **No multi-asset, no FX, no options, no income view** — not retirement-complete.
10. **Single-user, no auth, local-first.** Cloud deploy still pending. Daily cadence
    nudges overtrading; no tax-lot awareness.

**Engineering**
11. **Stale-dev-server gotcha:** a long-running Streamlit process that auto-reloads
    across code edits can throw stale-import errors (mitigated by fresh launches).
12. **No monitoring/alerting on the pipeline itself** (a silent yfinance failure just
    yields fewer rows). No CI.

---

## 13. Future Roadmap (ranked)

| # | Improvement | Impact | Complexity | Priority |
|---|---|---|---|---|
| 1 | **Composite Final Score** (blend technical+fundamental+sector+risk, configurable weights) | High | Low | **P0** |
| 2 | **Risk layer**: correlation matrix, vol-adjusted sizing, portfolio drawdown/beta | High | Med | **P0** |
| 3 | Broaden universe (S&P 500 scan via batched download) + add bonds/ETF asset classes | High | Med | P1 |
| 4 | Dampen/repurpose Expected Upside for non-positive names; calibrate Confidence | Med | Low | P1 |
| 5 | Robust backtest (out-of-sample, costs, benchmark-relative, equity curve) | High | High | P1 |
| 6 | Second data source / fallback (e.g., Stooq, Alpha Vantage free tier) + pipeline health alerts | Med | Med | P1 |
| 7 | Cloud deploy (Streamlit Cloud) + scheduled cloud refresh | Med | Low | P1 |
| 8 | Tax-lot awareness + rebalancing suggestions | Med | Med | P2 |
| 9 | Real NLP sentiment / LLM insights (paid, opt-in) | Med | Med | P2 |
| 10 | CI (GitHub Actions) running pytest + a smoke E2E | Med | Low | P2 |
| 11 | Insider transactions (SEC EDGAR Form 4) | Low–Med | High | P3 |

---

## 14. Managing a real $1,000,000 portfolio with this system — what would still make me uncomfortable

1. **The ranking would steer me into crowded momentum and out of quality dips.** With
   $1M, buying what's already extended near 52-week highs (and dumping anything under
   its 200-DMA) is exactly how you buy tops and sell bottoms. The Final Score has no
   valuation or mean-reversion brake.
2. **No correlation/sizing means hidden concentration.** Five "🟢" names could be 80%
   one factor (mega-cap tech). The system would happily green-light a portfolio that
   blows up together in a single drawdown. "Sector 58%" is the only guardrail.
3. **"Expected Upside 6.3%" / "Confidence 76" with real money is dangerous framing.**
   They are heuristics with no probabilistic backing or calibration; I'd never size a
   $1M position off them.
4. **Single-source, daily-snapshot data.** One bad Yahoo day → silently wrong prices/
   fundamentals → wrong P/L and signals, with no second source to catch it.
5. **No execution discipline, tax awareness, or horizon.** A daily "🔴 להימנעות" on a
   long-term holding could trigger a costly, taxable sell that contradicts the plan.
6. **Backtest can't justify trusting the signal at scale** — too few samples, no costs,
   no out-of-sample. I don't actually know the edge's real-money expectancy.
7. **No drawdown/kill-switch.** Nothing tells me "stop, regime turned" beyond a
   descriptive regime score; with $1M I'd want hard risk limits.

Bottom line at $1M: I'd use it as a **morning dashboard and idea/risk screener**, with
every actual trade gated by an independent risk framework (and likely a human advisor).

---

## 15. Final Scores

| Dimension | Score | Notes |
|---|---|---|
| Data Quality | **80** | Real, NaN-guarded, fast; but single free source, some flaky/derived fields |
| Fundamentals | **78** | 8 real metrics + weekly cache; ROIC/FCF derived & sometimes N/A; not in ranking |
| Technical Analysis | **88** | Solid, standard, transparent breakdown; momentum-centric |
| Sector Analysis | **85** | Real ETF-based RS/momentum/trend, sensible ranking |
| Portfolio Management | **70** | Good analytics & health/exposure; no correlation/sizing/rebalancing/tax |
| Alerts | **82** | Typed, real events; no intraday/real-time; insider missing |
| User Experience | **86** | Polished dark RTL, fast, transparent; minor tooling quirks, no auth |
| Reliability | **82** | Tested + artifact architecture; single-source data, no monitoring/CI |

### Overall: **82 / 100**

**Justification.** As *software*, this is a well-architected, tested, fast, transparent
platform that does exactly what it claims and is pleasant to use daily — that earns the
high UX/technical/reliability marks. As an *investment decision system*, it is an
excellent **monitoring and screening** layer with honest, explained metrics, but it
lacks the risk-management, valuation-weighting, correlation, and validated-edge
machinery that real capital demands. The headline weakness — a momentum-only Final
Score with no risk layer — is also the single highest-leverage fix (Roadmap P0). Close
that, add a risk/correlation layer, and this credibly moves into the low-90s as a
decision-support tool.

*Information only — not investment advice.*
