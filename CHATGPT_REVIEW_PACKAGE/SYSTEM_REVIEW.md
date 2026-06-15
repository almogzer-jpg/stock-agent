# SYSTEM_REVIEW.md — Stock Agent Pro

**Document type:** Architecture & system overview (for external CTO / investment review)
**System:** Stock Agent Pro — a free, single-source (Yahoo Finance) US-equity
investment-intelligence platform.
**Language of product:** Hebrew (RTL). **Language of this package:** English.
**Data source:** `yfinance` only — **no paid APIs, no alternative data**.
**Disclaimer:** Informational/educational only — **not investment advice**.

---

## 1. What the system is

A modular Python pipeline that, every weekday morning, scans a US-equity
universe, computes a transparent multi-factor score per stock, layers on a risk
model, sector intelligence, a portfolio decision engine, an institutional-style
backtest, and a trust/validation layer — then serves everything through a dark,
RTL Streamlit dashboard (11 tabs + a separate mobile experience), a daily HTML/Excel
email, and CSV/Excel exports.

**Design principle:** *every displayed number traces to real data or a clearly
labeled, documented formula — no fabricated values.* Missing inputs degrade
gracefully ("אין נתון" / renormalized weights), never silently zero-fill.

**Performance principle:** a nightly orchestrator (`run.py` + `scanner.py`)
precomputes all heavy work into JSON/CSV artifacts; the dashboard reads artifacts
and makes **zero live network calls** on load (except optional on-demand news),
so it opens in ~2–3 seconds.

---

## 2. Folder structure

```
stock-agent/
├── run.py                  # ORCHESTRATOR: watchlist scan → all artifacts + email
├── scanner.py              # Market-wide universe scan (two-phase) → universe.json
├── config.py               # All thresholds, paths, weights, feature flags
├── universe.py             # S&P500 + Nasdaq-100 constituents (Wikipedia, weekly cache)
├── market.py               # Indices, sector intelligence, market-regime score
├── risk.py                 # Risk Intelligence Engine (beta/vol/maxDD/correlation/portfolio)
├── decisions.py            # Portfolio Decision Engine (Increase/Hold/Reduce/Exit)
├── trust.py                # Trust & Validation engine (0-100 trust score)
├── portfolio.py            # Portfolio analytics (P/L, exposures, health)
├── proprietary.py          # Calculated indicators (fear&greed, breadth, capital flow…)
├── explain.py              # Rule-based why-buy / why-watch / why-avoid text
├── insights.py             # Daily Hebrew briefing (market/opportunities/risks/rotation)
├── events.py               # Earnings dates + analyst up/downgrades (best-effort)
├── assistant.py            # Free rule-based Hebrew Q&A (no LLM)
├── names.py                # Ticker → company name
├── charts.py               # matplotlib sparklines for the email
├── data_loader.py          # OHLCV loader (NaN-safe)
├── indicators/
│   └── technical.py        # RSI, moving averages, etc.
├── scanners/
│   └── breakout.py         # Breakout setup detection
├── ranking_engine/
│   ├── score.py            # Technical/Final Score (0-100) + transparent breakdown
│   ├── factor_scores.py    # technical/fundamental/news/sentiment/risk sub-scores
│   ├── composite.py        # Composite Final Score V2 (5-factor weighted blend)
│   └── interpret.py        # classify() → positive/watch/avoid + Hebrew summary
├── fundamentals/
│   └── fundamentals.py     # 8 fundamental metrics (yfinance), weekly cache
├── news/
│   ├── headlines.py        # Yahoo headlines
│   └── sentiment.py        # Keyword-lexicon sentiment (0-100)
├── alerts/
│   ├── center.py           # Typed alert generation (Alert Center)
│   ├── email_notifier.py   # Gmail SMTP HTML/RTL digest
│   └── notifier.py         # Console/file-log alerts
├── backtesting/
│   └── backtester.py       # Signal backtest (non-overlapping trades, OOS split)
├── dashboard/
│   ├── app.py              # Streamlit dashboard (11 tabs)
│   ├── mobile.py           # Separate mobile-first UI (Phase 16)
│   ├── theme.py            # Dark RTL theme / CSS
│   └── index.html          # Static self-contained snapshot
├── tests/                  # pytest suite — 13 files, 72 tests
├── data/                   # ARTIFACTS (gitignored outputs) + outputs/ timestamped set
├── watchlist.txt           # User watchlist
├── portfolio.csv           # User holdings (Ticker,Quantity,AverageCost)
├── email_config.json       # Gmail App Password (GITIGNORED — never committed)
└── requirements.txt
```

---

## 3. Modules (by responsibility)

| Layer | Modules | Responsibility |
|---|---|---|
| **Ingestion** | `data_loader`, `universe`, `market`, `fundamentals`, `news/headlines`, `events` | Pull prices/constituents/fundamentals/news from yfinance + Wikipedia |
| **Scoring** | `ranking_engine/score`, `factor_scores`, `composite`, `news/sentiment`, `market` (sector) | Technical, Fundamental, Sector, News, Risk → **Final Score V2** |
| **Risk** | `risk.py` | Beta, Volatility, Max Drawdown, correlation, portfolio risk |
| **Decisions** | `decisions.py`, `portfolio.py`, `explain.py` | Target allocation + Increase/Hold/Reduce/Exit + "what to do today" |
| **Validation** | `backtesting/backtester`, `trust.py` | Historical signal performance, OOS split, 0-100 trust score |
| **Discovery** | `scanner.py`, `proprietary.py` | Market-wide two-phase scan, 5 rankings, proprietary indicators |
| **Interpretation** | `interpret.py`, `insights.py`, `assistant.py` | Plain-Hebrew classification, daily briefing, Q&A |
| **Presentation** | `dashboard/app.py`, `mobile.py`, `theme.py`, `charts.py`, `alerts/*` | Dashboard, mobile UI, email, alerts |
| **Orchestration** | `run.py`, `scanner.py`, `config.py` | Nightly precompute → artifacts; central config |

---

## 4. Data flow

```
                       (nightly, run_daily.bat — Mon–Fri 09:00 IST, Task Scheduler)
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            │                          run.py                            │
            │  1. Load watchlist + ^GSPC (for beta)                      │
            │  2. Per stock: OHLCV → technical metrics → score_stock     │
            │  3. risk.risk_profile (beta/vol/maxDD)                     │
            │  4. fundamentals.get_fundamentals (weekly cache)           │
            │  5. news/sentiment (breakout candidates)                   │
            │  6. market.sector_intelligence + market_regime_score       │
            │  7. composite.composite_score → ScoreV2 + contributions    │
            │  8. backtester.backtest_signal → win rate / OOS            │
            │  9. trust.trust_score → TrustScore                         │
            │ 10. decisions.portfolio_decisions (if portfolio.csv)       │
            └─────────────────────────────┬─────────────────────────────┘
                                          │  writes artifacts ↓
   results.csv / results.xlsx     market_overview.json   closes.json   events.json
   alerts_center.json   backtest.json   system_health.json   portfolio.json
   data/outputs/<timestamp>_{daily_report.html, .xlsx, opportunities.csv, alerts.csv}
   + email (Gmail SMTP, HTML/RTL) + dashboard/index.html snapshot
                                          │
            ┌─────────────────────────────┴─────────────────────────────┐
            │     scanner.py ALL  → two-phase universe scan              │
            │     Phase A (cheap, ~500 tickers): technical + risk + mom  │
            │     Phase B (deep, top-40): fundamentals + composite + BT  │
            │     → data/universe.json (5 rankings)                      │
            └─────────────────────────────┬─────────────────────────────┘
                                          │
                            ┌─────────────┴─────────────┐
                            │  dashboard/app.py (Streamlit) │
                            │  READS ARTIFACTS — zero live  │
                            │  calls on load (~2-3s)        │
                            └───────────────────────────────┘
```

**Key artifacts the dashboard reads** (all in `data/`):
`results.csv` (latest scan, the "pointer"), `market_overview.json`,
`closes.json`, `events.json`, `alerts_center.json`, `backtest.json`,
`system_health.json`, `portfolio.json`, `universe.json`.

---

## 5. Dependencies

**Runtime (`requirements.txt`):**
`yfinance` (all market data), `pandas`, `numpy`, `openpyxl` (Excel),
`streamlit` (dashboard), `plotly` (charts), `matplotlib` (email sparklines),
`lxml` + `requests` (Wikipedia constituent scraping),
`pytest` + `pytest-cov` (tests).

**External services:** Yahoo Finance (prices/fundamentals/news/events),
Wikipedia (S&P 500 / Nasdaq-100 constituents), Gmail SMTP (email).
**No paid APIs. No database** — artifacts are flat JSON/CSV on disk.

**Internal dependency notes:**
- `ranking_engine/factor_scores` depends on `ranking_engine/score`.
- `scanner.py` depends on `universe`, `market`, `risk`, `decisions`, `composite`, `fundamentals`, `backtester`.
- `dashboard/app.py` reads **data** from artifacts but calls engines for
  **interpretation** (`classify`, `factor_scores`, `explain`, `score_breakdown`).
- `dashboard/mobile.py` reuses the same artifacts; desktop path is untouched
  (branch via `_is_mobile()` + `st.stop()`).

---

## 6. Current production score

From the internal `STOCK_AGENT_SYSTEM_REVIEW.md` (most recent validation):

| Dimension | Score | Notes |
|---|---|---|
| **Engineering readiness** | **≈ 92 / 100** | Works reliably, tested (72 tests), fast (~2-3s dashboard, ~95s full universe scan) |
| **Investment-product readiness** | **≈ 83 / 100** | Decision *depth* is the main gap (single data source, lexicon news, top-40 enrichment) |
| **Maturity** | **Late MVP / early production (personal use)** | All planned phases (1–16) implemented |
| **Tests** | **72 / 72 passing** | Pure-logic engines 85–100% covered; 38% total (I/O modules covered via E2E) |

---

## 7. Known weaknesses

1. **Single data source (Yahoo Finance).** No redundancy; a Yahoo outage or
   schema change stops the pipeline. No data-vendor cross-check.
2. **News sentiment is a keyword lexicon**, not NLP. Sarcasm/context/numbers are
   missed; score is a coarse positive-share proxy.
3. **Universe enrichment is capped at top-40.** In the market-wide scan, only the
   40 most technically-strong names get fundamentals/composite/backtest. So
   "undervalued" means *cheap among the technically strong*, not the whole-universe
   cheapest — a deliberate quality-over-breadth tradeoff.
4. **Russell 2000 is excluded** (no clean free constituent list at scale).
5. **Backtest samples are small** for many names; some have 0 historical signals,
   so trust falls back to weak/None — correct, but limits validation depth.
6. **Technical Score ≡ Final (technical) Score by design**, while Final Score V2 is
   the composite blend. The naming overlap can confuse; documented in SCORE_ENGINE.md.
7. **Beta/correlation use price history only** (no fundamental factor model).
8. **No transaction costs, slippage, taxes, or position sizing** in the backtest —
   it measures signal edge, not net realizable return.
9. **Fundamentals weekly-cached** — intra-week earnings revisions aren't reflected
   until the next refresh.
10. **No user authentication / multi-user isolation** — built for single personal use.

---

## 8. Maturity verdict

The **engineering** is solid: modular, configurable, tested, fast, with graceful
degradation and honest "no data" handling. The **investment product** is a
genuinely useful screening + decision-support tool for a single informed user, but
is **not** a substitute for a multi-source institutional platform — its edges
(single source, lexicon news, capped enrichment, shallow backtest samples) are
documented, not hidden. See `INVESTMENT_COMMITTEE_REPORT.md` for the
"$1,000,000 portfolio" assessment.
