# CHATGPT_REVIEW_PACKAGE — Stock Agent Pro

A self-contained package for an **external CTO / investment-committee review** of
Stock Agent Pro (a free, Yahoo-Finance-only US-equity investment-intelligence
platform, Hebrew/RTL product). **No source code is included** — only documentation,
data-grounded sample outputs, and architecture diagrams.

## How to review

Suggested reading order:

1. **`SYSTEM_REVIEW.md`** — architecture, modules, data flow, dependencies,
   production score, known weaknesses. *Start here.*
2. **`ARCHITECTURE_DIAGRAM.md`** — component + scoring-pipeline diagrams (Mermaid).
3. **`SCORE_ENGINE.md`** — every score with exact formulas & weights (Technical,
   Fundamental, Sector, News, Risk, Final Score V2).
4. **`RISK_ENGINE.md`** — beta, volatility, max drawdown, correlation, portfolio
   risk, risk-score methodology.
5. **`OPPORTUNITY_HUNTER.md`** — universe, two-phase scan, categories, ranking,
   filters, historical validation.
6. **`TRUST_VALIDATION.md`** — trust score, confidence, backtest + out-of-sample
   methodology.
7. **`DASHBOARD_WALKTHROUGH.md`** — all 11 desktop tabs + mobile, purpose / metrics
   / decision process.
8. **`SAMPLE_OUTPUTS/`** — real engine outputs (15/06/2026) for Market Overview,
   Mobile, Top Opportunities, Portfolio, Trust.
9. **`TEST_RESULTS.md`** — 72/72 tests, coverage, remaining risks.
10. **`INVESTMENT_COMMITTEE_REPORT.md`** — the "$1,000,000 portfolio" assessment:
    trust / concerns / failure modes / what to fix first.

## At a glance

| | |
|---|---|
| Data source | Yahoo Finance only (free) — no paid APIs |
| Ranking | Final Score V2 = Fundamental 35% · Technical 25% · Sector 20% · News 10% · Risk 10% |
| Universe | S&P 500 ∪ Nasdaq-100 (~500–514 names), two-phase scan ~95 s |
| Tests | **72 / 72 passing**; pure-logic engines 85–100% covered |
| Readiness | Engineering ≈ 92/100 · Investment-product ≈ 83/100 |
| Top risks | single data source · lexicon news · top-40 enrichment cap · shallow backtest |

## Honest disclaimers

- **Informational/educational only — not investment advice.**
- Sample outputs are real engine data; portfolio *holdings* are sample data.
- `SAMPLE_OUTPUTS/` uses data snapshots rather than PNG screenshots due to a
  browser-automation tooling limitation (documented in `SAMPLE_OUTPUTS/README.md`),
  not an application defect.
