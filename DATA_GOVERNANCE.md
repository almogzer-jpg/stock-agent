# DATA_GOVERNANCE.md — Stock Agent Pro (Step 0)
Binding rules for every datum the platform ingests, computes and displays.

## Source tiers
| Tier | Source | Used for | Trust posture |
|---|---|---|---|
| **1 (primary)** | Yahoo Finance via `yfinance` | Prices/OHLCV, statements, analyst targets, holders, events | Good free coverage; unofficial API — must be cross-checked where possible |
| **2 (validation)** | **ECB via Frankfurter API** (official fixing) | FX cross-check: USD/ILS, EUR/USD | Authoritative for FX; daily fixing (±1.5% tolerance vs live) |
| **2 (validation, best-effort)** | Stooq CSV | Index cross-check (S&P, Dow) + price fallback | Free; blocks some networks — treated as best-effort |
| **3 (derived)** | Our engines (`ranking_engine`, `technicals`, `proprietary`…) | All scores/levels/decisions | Deterministic, unit-tested, always labeled "מחושב" |

## Refresh frequency
Daily GitHub Action (04:00 UTC, Mon-Fri): full pipeline → commits `data/` snapshot.
Deep-dive page: live Tier-1 fetch per ticker, 30-min cache. `reliability.json` regenerated
on every pipeline run (includes cross-check results + freshness).

## Fallback rules
1. Tier-1 series missing → try Tier-2 (implemented for global FX/indices; row carries
   `source: "Stooq (גיבוי)"`). 2. No source at all → display **"אין נתון זמין"** — never a
   stale copy presented as current, never an invented value.

## Cross-validation & conflict resolution
- Compared series: USD/ILS + EUR/USD vs **ECB**; S&P + Dow vs Stooq (best-effort).
- Tolerance: 1.0% (market-vs-market), 1.5% (market-vs-ECB-fixing).
- |diff| ≤ tolerance → agree. |diff| > tolerance → **status "disagreement"**: reliability
  label forced to "נמוכה — מקורות סותרים", banner in ⚙️; the Tier-1 value is still shown
  (with the warning) — we do not silently pick a "winner".
- Secondary unreachable → status **"not_completed"** displayed as-is; never silently verified.

## Outlier & sanity rules
Engine-level guards (existing): NaN closes dropped; support/resistance require ≥0.1% margin
(no self-levels); scores clamped 0-100; missing fundamentals renormalize composite weights.
Pipeline: a scan yielding <50% of expected tickers marks `system_health.failed_pulls`.

## Stale-data rules
Artifact older than **3 days** (`reliability.STALE_AFTER_DAYS`) → status `stale` →
flagged in the global provenance footer + ⚙️; reliability freshness factor drops to 10/35.

## Conclusion-suppression rules
- Reliability label "נמוכה" / crosscheck "disagreement" → conclusions must degrade to
  "אינדיקציה בלבד" (UI enforcement lands in Step 1; scoring cap live now).
- Score "גבוהה" (≥75) is IMPOSSIBLE without an agreeing independent second source (cap 74);
  partial cross-check coverage caps at 92. Encoded in `reliability.reliability_score` + tests.

## Ownership
`data/` is written by the pipeline/bot only. Humans commit code, not data. On git conflicts
in `data/` — always take the newer pipeline version (`git checkout --theirs`).
