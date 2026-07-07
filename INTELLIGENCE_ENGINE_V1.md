# Investment Intelligence Engine V1 — Roadmap
**The competitive core of Stock Agent Pro.** UI is table-stakes now; from here, the moat is analysis quality.
Hard rules: free data only · deterministic & reproducible · evidence-first · labeled (עובדה/מחושב/היסטורי/תרחיש) · "אין נתון זמין" over invention · confidence gates every conclusion.

**Baseline (already live):** fundamental score (8 metrics) · technical engine (S/R+volume-confirm, R/R, entry quality, MACD/ATR/MTF-lite) · valuation score (PEG/FwdPE) · risk engine (β/vol/DD) · scenarios (analyst targets + model likelihood) · trust/confidence (7 factors) · full score decomposition. V1 = deepen each into a true engine.

---

## E1 — Fundamental Engine (upgrade)
| Capability | Free-data path | Status |
|---|---|---|
| Revenue/margin/FCF **trends** (multi-year direction, not snapshot) | yfinance annual+quarterly statements (4y) → slope/consistency scores | NEW |
| ROIC/ROE quality + stability | statements history | extend |
| Debt analysis (net debt/EBITDA, interest cover, maturity proxy) | statements | NEW |
| **Dilution** (share count trend) | shares outstanding history | NEW |
| **Capital allocation** (buybacks vs dilution, capex ratio, FCF usage) | cashflow statements | NEW |
| Insider ownership | `major_holders` (insider %, inst %) — real | NEW |
| Management quality | **no free structured source** → proxy = capital-allocation score + execution consistency, labeled "פרוקסי מחושב" | honest proxy |
| Moat assessment | quantitative proxy only: margin stability + ROIC persistence + share retention, labeled "אינדיקציית חפיר מחושבת" — never narrative claims | honest proxy |
**Output:** Business Quality Score (decomposed) + trend arrows per metric (↑→↓) feeding the Delta Engine later.

## E2 — Technical Engine (upgrade)
- Multi-timeframe: weekly-resampled trend/RSI alongside daily → alignment score ("יומי ושבועי מסכימים").
- Volume profile (lite): volume-by-price histogram from 6m OHLCV → high-volume nodes as S/R reinforcement.
- Relative strength vs sector ETF and vs SPX (have vs SPX at sector level → add per-stock).
- **Breakout probability / mean-reversion probability = historical frequencies** from our own backtester (e.g. "בעבר, פריצות במניה זו החזיקו 62% מהמקרים, n=13") — labeled historical observation, never a forecast.
- Entry quality v2: blend distance-to-levels + MTF alignment + volume node proximity.

## E3 — Valuation Engine (the biggest V1 leap)
- **DCF (deterministic, labeled "מודל שקוף"):** FCF base → growth = blended (hist CAGR capped + analyst if present) → 3 discount scenarios → per-share fair-value **range**, all assumptions displayed and user-adjustable later.
- **Peer comparison:** sector median multiples computed from OUR universe scan (we already enrich 40; expand enrichment breadth for medians) → "PE 30 מול חציון סקטור 22".
- Historical valuation: current multiple vs the stock's own 3-5y range (percentile).
- Fair-value range = triangulation (DCF range ∩ peers ∩ history) → margin of safety vs range midpoint; verdict Undervalued/Fair/Overvalued with the three evidence lines shown.

## E4 — Risk Engine (from score → assessment)
8 named risks, each = metric + threshold + WHY sentence: Business (revenue volatility, margin trend), Financial (leverage, interest cover, dilution), Valuation (percentile vs history/peers), Macro (β, rate-sensitivity via sector, USD exposure proxy), Technical (below MAs, breakdown status), Execution (earnings-consistency history), Regulatory (sector map — labeled general), Liquidity (avg $ volume, spread proxy). Output: risk matrix card, every cell clickable to its evidence.

## E5 — Scenario Engine (upgrade)
- Targets: analyst high/mean/low (have) + **model targets** from E3 fair-value range (bear=low bound, base=mid, bull=high) — two labeled sources side-by-side.
- Probabilities: keep deterministic model-likelihood + add historical calibration (how often did +X% happen within horizon, from price history) — labeled frequency.
- Key assumptions listed per scenario (growth, margin, multiple used).

## E6 — Confidence Engine (upgrade)
Extend trust with: data **freshness** (statement age, price age), indicator agreement (MTF + fund/tech alignment), market regime stability, sample sizes. Confidence <40 ⇒ conclusions auto-soften to "אינדיקציה בלבד" (UI-enforced). Never certainty at low confidence.

## E7 — Explainability Engine (platform-wide contract)
Every displayed score exposes: inputs → formula/weights → contributions → data as-of → source. One reusable "למה?" expander component; glossary page; provenance line on every analytical card. (This is a UI contract + registry of explain-functions per metric.)

---

## Phasing & effort
| Phase | Content | Effort |
|---|---|---|
| **I-1** | E3 DCF+peers+history (valuation leap) + E7 explain-component | High — biggest differentiation |
| **I-2** | E1 trends/dilution/cap-allocation/insiders | Medium |
| **I-3** | E4 risk matrix + E6 freshness/agreement | Medium |
| **I-4** | E2 MTF/volume-profile/probabilities | Medium |
| **I-5** | E5 dual-source scenarios + calibration | Low-Medium |
Sequenced AFTER the pre-release criticals (cloud refresh, skeleton, consolidation) — intelligence without fresh data is worthless. Each engine ships with pure functions + unit tests + the Quality Gate.

---

# E0 — Investment Decision Engine (the brain, above all engines)
**Purpose:** think like a 20-year PM — not compute indicators, but SYNTHESIZE all engines (E1-E7 + regime/sector/sentiment/liquidity/earnings inputs) into one coherent, conflict-resolved decision. Every recommendation in the platform ultimately flows from E0. Deterministic, rule-based, fully explainable — "thinking", not black box.

## Conflict-resolution matrix (the core IP — examples, extensible ruleset)
| Situation (engine signals) | Resolution |
|---|---|
| עסק מצוין + תמחור גרוע | **Wait** — "חברה לרשימת המתנה; מחיר יעד כניסה מה-E3" |
| תמחור זול + עסק חלש | **Avoid** — מלכודת ערך (value trap) |
| פריצה טכנית חזקה + פונדמנטל חלש | **Trade-only** — אופק קצר, סווינג בלבד, לא השקעה |
| חברה מצוינת + שוק דובי (regime) | **Accumulate-slowly / Watch** — איכות כן, תזמון לא |
| עסק+תמחור+טכני מיושרים | **Highest conviction** — Strong Buy, הקצאה מלאה |
| ביטחון (E6) נמוך בכל שילוב | downgrade אוטומטי לרמה זהירה + "אינדיקציה בלבד" |
| סיכון נזילות/מינוף קיצוני | cap קשיח על ההמלצה בלי קשר לשאר |

## Mandatory outputs (per ticker)
1. **Final decision** — 9-level scale: Strong Buy · Buy · Accumulate · Watch · Hold · Wait · Reduce · Sell · Strong Sell (supersedes today's 6-level).
2. **Confidence 0-100** (from E6; gates language).
3. **Decision summary** — one sentence, human PM voice.
4. **Top reasons FOR** — ranked by contribution weight.
5. **Top reasons AGAINST** — ranked.
6. **Upgrade path** — what must change to raise the rating (explicit thresholds: "תמחור מתחת ל-X / פריצת $Y").
7. **Thesis invalidators** — measurable kill-conditions (feed future Signals/Watchlist).
8. **Expected holding period** — swing / 3-6m / 6-12m / 12m+.
9. **Suitable investor types** — Income/Growth/Value/Momentum/Swing/Long-term/Institutional (multi-tag).
10. **Monitor next quarter** — 3-5 named metrics with current values.

## Implementation notes
- v0 exists today (`deepdive.investment_decision`) — E0 replaces it once E1-E7 mature; same pure-function + tests pattern; the conflict matrix is a declarative rule table (testable row-by-row).
- Sentiment/liquidity/earnings inputs start from existing proxies (news score, $ volume, earnings dates) and deepen with the engines.
- UI contract: the Decision Card everywhere renders ONLY E0 output; every element clickable to its evidence (E7).
- Phasing: E0-lite lands with I-1 (consumes current engines through the new conflict matrix + 9-level scale); E0-full after I-3.
