# FULL_PRODUCT_AUDIT — Stock Agent Pro (Cycle 1)
Date: 12/07/2026 · Evidence: live local app (current env, port 8502) + clean-env repro (newest
package stack, port 8503) + DOM verification of every page (this session) + fresh screenshots
(desktop home, mobile home) + cloud incident data. 106 unit tests green at audit time.

## 0. Performance baseline (measured — Part 11 "measure first")
| Metric | Value | Method |
|---|---|---|
| Initial HTML load (artifact pages) | **2.07s** | urllib timing, cold session |
| Unit suite | 106 tests / ~0.6-1.3s | pytest |
| Company deep-dive first load | ~8-12s | live yfinance fetch (observed repeatedly); 30-min cache after |
| Daily pipeline (clean Ubuntu, Action) | run.py ~40-60s · scanner ALL ~2min | green bot runs |
| Artifact sizes | universe.json 330KB (largest) | zip audit |
| Cold clean-install | pip → boot OK | clean venv + GitHub Action |

## 1. CRITICAL findings (P0)
1. **pandas-3 regression:** on the newest stack (pandas 3.0.3 — what fresh cloud deploys
   install) the Home KPI cards render **0** (`.kpi` count 0; chips/tables fine; **no
   exception** — silent loss). Reproduced on clean venv. Root cause TBD (suspect NaN/`.empty`
   semantics in the KPI block). Any cloud redeploy can silently degrade Home.
2. **Selection bias in discovery (Part 7 confirmed in code):** scanner Phase B enriches only
   the top technical subset (~40); value/quality/turnaround rankings draw from that enriched
   pool → a cheap-but-technically-weak company can never appear "undervalued". Ranking pool
   labels are ambiguous in UI.
3. **Reliability layer missing:** no per-output source+timestamp+completeness. As-of exists
   only on: global strip, MI page, sidebar caption. Trust≠Reliability not distinguished.
4. **"יעד (מחושב)" home column** is a heuristic (price×ExpectedUpside). It IS labeled, but
   ExpectedUpside itself still reads forecast-like in places (Part 8 rule) — needs rename/
   confidence framing everywhere it appears.

## 2. Page-by-page (question · 5-sec grasp · gaps)
### 🏠 ראשי (Today)
- **Question:** what matters this morning. **5-sec:** regime+summary+strip land well
  (screenshot evidence). **Unclear:** *what changed since yesterday* — nowhere (no Delta Feed;
  snapshots exist in data/outputs but unused). **Duplication:** exec-summary sentence vs
  "תובנת היום" card overlap; hot-stocks "מומנטום" list vs table momentum. **Noise:** 12
  sections still compete; events panel thin (earnings only). **Missing:** VIX movement in
  brief; data-freshness statement; weekly change on strip chips; explicit "USD/ILS = כמה ₪
  לדולר"; trust column removed from table (needed per Part 3D). **Verdict:** restructure to
  Morning Brief + Delta Feed on top; strip+table upgrades; merge insight into brief.
### 🔎 ניתוח חברה
- **Question:** buy now / wait / why. **5-sec:** header+decision card excellent. **Unclear:**
  data completeness & last-update not above the fold; scores→claims not linked to sources.
  **Missing (Part 4):** trend columns in fundamentals (only snapshots), fair-value **range**
  (single analyst mean shown), peer comparison, dilution/cap-allocation, MA100 in UI row,
  business/segments (only description). **Noise:** page very long — financials/scores/thesis
  all open; exec-summary duplicates decision card strengths/risks. **Perf:** 8-12s with
  spinner only. **Verdict:** fold sections per Part 4 order; add completeness+as-of to header;
  E1/E3 engines fill trends+range (blueprint).
### 💎 הזדמנויות
- Filter form + grid work; grid still visually "native" (dark now, acceptable). **Missing:**
  pool labeling per ranking (bias, P0-2); tags derive from enriched subset. Score V2 info card
  occupies fixed space (should fold). **Duplication:** none since sector move ✓.
### 🗺️ סקטורים (rebuilt this week) — meets bar; missing rank-change (needs delta engine) and
  1M/3M momentum split; "כניסת/יציאת הון" wording on Home must carry the estimated-proxy label
  everywhere (it does in caption — keep enforced).
### 🚨 התראות — action-center OK. Missing: severity for "מידע" items sometimes noisy; no
  event-impact ranking. Minor.
### 📊 אינטליגנציית שוק — global tabs good (as-of ✓). Scored table + backtest raw
  (dataframe), backtest single-signal caveats not displayed prominently (Part 8). System-health
  metrics exist but not the full System Quality card (Part 5). **Verdict:** absorb: global →
  stays; health → Settings/System card; backtest → company page + validation page later.
### ⚙️ הגדרות — thin; no freshness warning (stale>3d), no source status. **Verdict:** becomes
  System Quality home.
### Mobile (screenshot evidence)
- Bottom nav ✓ chips ✓. **Findings:** KPI cards waste vertical space at width>500 (huge empty
  cards); opp-card has large empty area, analyze button low-contrast thin; nav labels slightly
  clipped at some widths; Today shows 6 cards (spec: regime, main change, top-3, sector change,
  top alert, strip — "main change" impossible without delta). Analysis page lacks decision
  summary sentence (has card). No horizontal overflow ✓.
### States
- Loading: spinner-with-text only; skeleton class exists but unused (deep-dive!). Empty states:
  present on scanner/alerts/sectors ✓, inconsistent phrasing. Error states: guarded perf
  section ✓; deep-dive error banner ✓.

## 3. Parts 5-8 gap table
| Area | Exists | Gap |
|---|---|---|
| Confidence | trust engine (7 factors) ✓ | not split from *reliability*; no per-datum freshness/completeness display |
| Governance | single source; bot refresh ✓ | no DATA_GOVERNANCE.md, no cross-check source, no stale rules surfaced |
| Scanner | 5 ranking lists ✓ | single technical gate → bias; pools unlabeled |
| Backtest | breakout signal + IS/OOS + confidence label ✓ | one family; no costs/slippage; avg-only; no regime stability; "expected upside" framing |

## 4. Design-system compliance
Emoji-as-icons persists in KPI/k-ico (HIG panel flagged); 3 card + 3 badge classes pending
consolidation; focus-ring missing; glossary missing; toggle contract differs desktop/mobile.
Contrast/typography/RTL: compliant (tests + DOM). Excess green: bounded ✓.

## 5. What deserves REMOVAL/merge
Home: standalone "תובנת היום" card (→ Morning Brief); hot-stocks momentum list (dup of table
sort). MI page: dissolve (global→keep as page? → see blueprint). Company: exec-summary card's
strengths/risks (dup of decision card) → keep description only. Mobile: oversized KPI cards.
