# V2_IMPLEMENTATION_BLUEPRINT — Stock Agent Pro (Cycle 2)
Companion to FULL_PRODUCT_AUDIT.md. Implementation begins only after user approval.
**Git checkpoint first (Rule 15): tag `v2-pre` before step 1.**

## Order of work (per directive Part "Cycle 3", adjusted by audit severity)
### Step 0 — P0 hotfix (before everything)
- Fix pandas-3 KPI regression (silent Home degradation on fresh deploys). Repro exists
  (clean venv). Add a pandas-3 CI leg: run tests on latest stack in the GitHub Action.
### Step 1 — Reliability & source visibility (Part 5+6)
- `reliability.py` (pure): per-artifact record {source, as_of, age_days, completeness %,
  missing_fields, method, external|calculated, reliability_score (source-quality/freshness/
  completeness/sample/agreement), limitation}. Trust (signal agreement) stays separate.
- UI: provenance footer component (one reusable fn) on every analytical card/page; System
  Quality card in ⚙️ (pulls/failures/stale/scan counts/avg completeness+reliability).
- DATA_GOVERNANCE.md (tiers, refresh, fallback, conflict, outlier, stale, suppression rules).
- Cross-check source (prices/indices/FX): **Stooq** (free CSV) — verify agreement on price/
  d1/major indices/USDILS; disagreement >1% → flag "cross-validation failed" (never silent).
- Suppression rule: reliability<threshold ⇒ conclusions render as "אין מספיק מידע אמין".
### Step 2 — Today rebuild (Part 3)
- **Delta engine (lite):** diff latest two data/outputs snapshots (already saved daily) →
  deltas.json {score/trust/risk/sector-rank/momentum/S-R/valuation changes, new/removed
  opportunities, regime change} + measurable cause from contribution columns (Contrib* exist!).
- Morning Brief card (deterministic; regime+breadth dir+VIX d1+strong/weak sector+counts+top
  change). Delta Feed section (top 5-8 by materiality). Strip: add weekly %, source+timestamp
  line, USD/ILS explanation tooltip; add trust column + upside-to-resistance/downside-to-
  support columns to the table (data exists since P24). Remove dup insight card + momentum
  hot-list. Events: fold analyst revisions in (exists), label coverage honestly.
### Step 3 — Company Analysis (Part 4)
- Header: + last-update, completeness, reliability badge. Decision summary: add "אין מספיק
  מידע אמין" gate (Step 1). Fold sections into report order (business→financial→growth→
  valuation→technical→risks→scenarios); remove dup strengths/risks from exec summary.
- E1-lite trends (4y statements: revenue/margins/FCF slope arrows + dilution) — feeds
  fundamentals "trends not snapshots". E3-lite fair-value RANGE: analyst low/mean/high +
  sector-median multiple check (universe medians) — labeled assumptions; margin-of-safety vs
  range. Skeleton loading (staged: header→decision→rest) targeting perceived <4s.
### Step 4 — Scanner correction (Part 7)
- scanner.py: independent passes — momentum/value/quality/turnaround/low-risk/near-support/
  breakout computed on the FULL scanned universe metrics (phase-A fields suffice for value=
  Valuation-proxy? value needs fundamentals → run light fundamental fetch for value/quality
  pass candidates independent of technical gate; cap batch sizes). Each ranking carries
  `pool` label ("מהיקום המלא"/"מבין המועשרות") shown in UI.
### Step 5 — Global & Sectors — sector rank-change from delta engine; 1M momentum column;
  keep proxy labels enforced.
### Step 6 — Mobile (Part 10) — Today per spec (main-change from delta; trim to 6 blocks);
  compact KPI cards (fix wasted space, button contrast); analysis adds one-line decision
  summary; keep lazy charts. Verify 390/430 via resize + real device ask.
### Step 7 — Performance (Part 11) — after-measurements vs baseline table (audit §0);
  parallelize deep-dive fetches (statements/targets concurrent), move translation off critical
  path (background/after-render), memoize name lookups; report before/after.
### Step 8 — Testing & monitoring (Part 12)
- Tests: artifact schema regression; provider-mock integration; stale-data; source-conflict;
  latest-stack (pandas3) matrix; UI smoke via streamlit AppTest (nav+pages render).
- Monitoring: Action step alerts on failed run/partial scan/empty opportunities/stale
  artifacts (writes status into system_health; ⚙️ shows red).
### Step 9 — Backtest upgrade (Part 8, after engines)
- Families: breakout/near-support-bounce/momentum-continuation; costs+slippage params;
  distribution stats (win rate, median, p10/p90, MAE/MFE), regime split, walk-forward; rename
  "Expected Upside"→"פוטנציאל מחושב (היוריסטי)" everywhere + calibration note; suppress
  probability-language without calibration.
### Cycle 5 — V2_RELEASE_READINESS.md with honest scores.

## Reuse / Remove
- **Reuse:** theme components, sectbl tables, decision card, S/R+perf engines, views.py,
  delta source = existing outputs snapshots, Contrib* columns for delta "why".
- **Remove:** Home insight card, hot-momentum list, exec-summary dup halves, MI page shell
  (global→"🌍 שווקים" page name; health→⚙️; backtest→company/validation).

## Data changes
New artifacts: deltas.json, reliability.json (or fields inside existing), governance doc.
Schema versioning: add "schema": N to artifacts + regression tests.

## Migration risks
- app.py monolith (~1700 lines) — splice edits risky → **extract pages to dashboard/pages_*.py
  modules during Steps 2-3** (mechanical, test-guarded).
- pandas-3 behavior differences beyond KPI bug — mitigated by CI matrix leg (Step 0).
- Cloud deploys pick latest deps — pin upper bounds? Decision: pin major versions in
  requirements (pandas<4, streamlit<2, yfinance<2) after matrix passes.
- Scanner Step 4 increases scan time — budget +60-90s in Action; measure.

## Performance targets
Artifact pages ≤3s (keep) · deep-dive perceived ≤4s (skeleton) / full ≤8s · scan ≤4min ·
zero duplicate name/fundamental lookups (cache hits logged).

## Test plan gates (per step)
Unit green + new step-specific tests + DOM desktop + ?m=1 + latest-stack leg + benchmark note.
