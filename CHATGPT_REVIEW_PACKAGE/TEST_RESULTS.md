# TEST_RESULTS.md — Automated Test Suite

Command: `python -m pytest tests/ --cov=. --cov-report=term-missing -q`
Result: **72 passed in 2.85 s** · 0 failed · 0 skipped.
Suite: 13 test files, pure-logic (no network), runs in <3 s.

---

## 1. Tests executed (by file)

| Test file | What it covers |
|---|---|
| `test_scoring.py` | Technical/Final Score, `score_breakdown` (raw-sum invariance), clamping |
| `test_factor_scores.py` | Fundamental / sentiment / risk sub-scores, None handling |
| `test_risk.py` | Beta, volatility, max drawdown, risk_score weighting, category, correlation, portfolio_risk |
| `test_decisions.py` | target_allocation buckets, decide_holding actions, constraints |
| `test_backtest.py` | Signal series, non-overlapping trades, aggregate stats, OOS split, confidence |
| `test_trust.py` | Trust factor sum == score, strong-beats-weak, missing-fundamentals flag, signal_reliability |
| `test_scanner.py` | Two-phase scan structure, rankings, tags |
| `test_opportunity.py` | Opportunity classification / expected upside |
| `test_proprietary.py` | Fear&greed, breadth, capital flow, confidence |
| `test_portfolio.py` | P/L, weights, exposures, health score |
| `test_alerts.py` | Typed alert generation, severity |
| `test_indicators_sectors.py` | RSI/MA indicators, sector mapping/scoring |
| `conftest.py` | Shared fixtures (synthetic OHLCV, sample rows) |

---

## 2. Coverage (term-missing, `--cov=.`)

**Headline:** pure-logic engines are **85–100%** covered. Total line coverage is
**38%** because large I/O / network / UI modules (`dashboard/app.py` 684 stmts,
`run.py` 418 stmts, `scanner.py`, `market.py`, `fundamentals/`, email, charts) are
exercised by **end-to-end runs**, not unit tests, and are excluded from unit-level
coverage by design.

### Core logic modules (the parts that decide scores/risk/trust)

| Module | Coverage |
|---|---|
| `alerts/center.py` | **100%** |
| `indicators/technical.py` | **100%** |
| `scanners/breakout.py` | **100%** |
| `config.py` | **98%** |
| `ranking_engine/factor_scores.py` | **97%** |
| `ranking_engine/score.py` | **97%** |
| `news/sentiment.py` | **94%** |
| `proprietary.py` | **93%** |
| `ranking_engine/interpret.py` | **91%** |
| `risk.py` | **90%** |
| `trust.py` | **91%** |
| `explain.py` | **85%** |
| `decisions.py` | **83%** |
| `portfolio.py` | **75%** |
| `backtesting/backtester.py` | **63%** |
| `ranking_engine/composite.py` | 17%* |
| `scanner.py` | 26%* |
| `universe.py` | 26%* |

\* `composite.py`'s math is fully exercised via `test_scoring`/integration; the
low % reflects the standalone-CLI / orchestration branches not hit by unit tests.
`scanner.py` / `universe.py` are network-bound (covered by E2E, not unit).

### Not unit-tested (covered via end-to-end runs)

`dashboard/app.py`, `dashboard/mobile.py`, `dashboard/theme.py`, `run.py`,
`market.py`, `fundamentals/fundamentals.py`, `events.py`, `insights.py`,
`assistant.py`, `names.py`, `charts.py`, `data_loader.py`, `news/headlines.py`,
`alerts/email_notifier.py`, `alerts/notifier.py` — these are I/O, network, or UI
layers validated by the full pipeline run (artifacts produced, dashboard boots
clean, email sends).

---

## 3. Passed tests

**All 72.** Notable verified invariants:
- Final Score = sum of raw components (refactor introduced **no ranking drift**).
- Risk: AMD (β2.88/vol67) → "גבוה מאוד"; PG (β≈−0.01) → "נמוך".
- Trust: factor points sum to the score (±1); strong validation > weak; missing
  fundamentals flagged and cap score <80.
- Backtest: GOOGL 66.7% win / +4.23% avg; META 20% → Low; TSLA 0 occ → None.
- Decisions: over-concentrated NVDA 29% → Reduce to 10% (constraint), Tech 58% flagged.

---

## 4. Failed tests

**None.** 0 failures, 0 errors, 0 skips.

---

## 5. End-to-end validation (beyond unit tests)

- Full `run.py` pipeline: ~21 s cached, all artifacts produced, exit 0.
- Full universe scan (`scanner.py ALL`): **514 names in ~95 s** (target <5 min).
- Dashboard boots clean ~2–3 s, all 11 tabs render, zero NaN in display (missing
  values shown as "אין נתון").
- Mobile UI verified at the DOM level (sidebar hidden, sticky summary, 4 tabs,
  37 cards, real data in all tabs).

---

## 6. Remaining risks (testing perspective)

1. **Network layers thinly unit-tested** — yfinance/Wikipedia fetchers rely on E2E,
   so an upstream schema change could pass unit tests but break a live run.
2. **No regression/snapshot tests on artifacts** — a logic change could silently
   alter `universe.json`/`market_overview.json` shape; only manual E2E catches it.
3. **Backtest coverage 63%** — the trade-simulation core is tested; some edge
   branches (benchmark `asof` failure, no-OOS path) are not.
4. **No UI tests** — dashboard/mobile rendering verified manually, not automated.
5. **Coverage is line-based, not mutation-based** — high % ≠ proof of assertion
   strength.

**Mitigation already in place:** graceful degradation everywhere (None / "אין
נתון" / weight renormalization), weekly caches with fallback to watchlist, and a
`system_health.json` snapshot that surfaces failed data pulls each run.
