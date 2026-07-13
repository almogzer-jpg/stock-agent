# RELIABILITY.md — How trust works in Stock Agent Pro (Phase 0.5)
For contributors. Companion to `DATA_GOVERNANCE.md`. Code: `reliability.py`, `crosscheck.py`.

## Two distinct concepts
- **Confidence (trust.py):** do the *signals* agree, and did they validate historically?
- **Reliability / Data Confidence (reliability.py):** is the underlying *data* trustworthy
  enough to support any conclusion? A brilliant signal on stale/unverified data is worthless.

## Data Confidence Score (`reliability.data_confidence`)
Weights: completeness 30 · freshness 20 · source quality 20 · cross-validation 15 ·
multi-source 10 · consistency 5; fallback −10.
**Hard caps:** single unvalidated source ≤79 (never High/Institutional); platform-level score
without a successful cross-check ≤74; partial cross-check coverage ≤92.
Bands: ≥93 Institutional · ≥80 High · ≥65 Moderate · ≥40 Low · else Very Low
(`conf_band`, Hebrew labels included). One verbal scale platform-wide.

## Source ranking & fallback hierarchy
Tier 1 Yahoo (primary, everything) → Tier 2 ECB/Frankfurter (FX validation, official) +
Stooq (indices validation + price fallback, best-effort) → derived engine values (Tier 3,
always labeled "מחושב"). Missing everywhere ⇒ "אין נתון זמין" — never estimated silently.
Fallback rows carry `source: "Stooq (גיבוי)"`.

## Cross-validation logic (`crosscheck.run_crosscheck`)
USD/ILS + EUR/USD vs ECB (tolerance 1.5% — official fixing vs live market), S&P + Dow vs
Stooq (1.0%). Statuses: `ok` / `disagreement` (forces "נמוכה — מקורות סותרים") /
`not_completed` (displayed as-is; never silently verified). Runs in the daily pipeline;
results persisted in `data/reliability.json`.

## Quality gate (`reliability.quality_gate`)
Before displaying an analysis the UI verifies: freshness ✓ · data-confidence ≥45 ✓ ·
no critical missing fields (price, price history) ✓ · no source disagreement ✓.
Fail ⇒ the recommendation is suppressed and replaced with
**"אין מספיק מידע אמין כדי לגבש מסקנה"** + the concrete reasons; raw data remains visible.

## Explainability
Every recommendation shows its breakdown (`deepdive._decision_breakdown`): per-dimension
contribution points from the composite model (reproducible) + "⛔ blockers" — the weakest
dimensions (<55) that prevented a higher rating.

## Audit trail & history
- `data/decision_audit.jsonl` (git-ignored, append-only): per analysis — ticker, ts, version,
  sources, models, weights, missing fields, confidences, gate result → full reproducibility.
- `data/rec_history.json` (git-ignored): per-ticker daily recommendation/confidence/score/
  target/risk history (30 entries) → self-consistency tracking, shown in the analysis page.
- Local persistence v1; server-side persistence arrives with the backend phase.

## Surfaces
Provenance footer on every page · "📚 מקור הנתונים" expander + reliability badge + quality
warnings on the analysis page · full reliability card in ⚙️ · internal diagnostics at
`?diag=1` (source health, fallback usage, freshness, last audit records).
