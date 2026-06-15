# SCORE_ENGINE.md — Scoring Methodology

Detailed specification of every score, with **exact formulas and weights as
implemented in source** (`ranking_engine/`, `news/sentiment.py`, `market.py`).
All scores are 0–100. Higher = better, **except Risk Score** (higher = riskier),
which enters the composite as *risk health* = `100 − risk`.

---

## 0. Score map

| Score | File / function | Range | Role |
|---|---|---|---|
| Technical / Final Score | `ranking_engine/score.py::score_stock` | 0–100 | Momentum/trend quality; **the "Final Score"** and the Technical dimension of V2 |
| Fundamental Score | `ranking_engine/factor_scores.py::fundamental_score` | 0–100 / None | Valuation + quality |
| Sector Score | `market.py::sector_intelligence` (+ `sector_score_for`) | 0–100 | Strength of the stock's sector |
| News Score | `news/sentiment.py::score_headlines` | 0–100 (50 neutral) | Headline sentiment |
| Risk Score | `risk.py::risk_score` (portfolio) / `factor_scores.risk_score` (per-stock fallback) | 0–100 (higher = riskier) | Volatility/beta/drawdown |
| **Final Score V2** | `ranking_engine/composite.py::composite_score` | 0–100 | **Weighted blend of all five — the ranking score** |

---

## 1. Technical Score (= "Final Score") — `score.py`

Five components, **summed raw** then clamped to 0–100 (no per-component rounding,
so there is no ranking drift). Component weights (max points):

| Component | Max pts | Rule |
|---|---|---|
| **Trend structure** | 25 | +8 if Price > MA50; +9 if Price > MA200; +8 if MA50 > MA200 (golden alignment) |
| **Proximity to 52-week high** | 20 | `max(0, 20·(1 − DistFromHigh%/20))` → at high = 20, ≥20% below = 0 |
| **RSI momentum** | 20 | 20 if 50 ≤ RSI ≤ 75; 10 if 40 ≤ RSI < 50; 8 if 75 < RSI ≤ 80; else 0 |
| **Volume confirmation** | 20 | ≥1.5× avg = 20; linear `20·(VolRatio−1)/(1.5−1)` between 1.0× and 1.5×; <1.0× = 0 |
| **Short-term posture** | 15 | 15 if Price > MA20; else 0 |

```
Final/Technical Score = clamp( trend + proximity + rsi + volume + short_term , 0, 100 )
```

Thresholds (`config.py`): `NEAR_HIGH_PCT=10`, `VOLUME_SPIKE=1.5`, `RSI_MIN=50`, `RSI_MAX=75`.
`score_breakdown()` exposes rounded per-component points for the UI "how is this
score built" panel.

> **Naming note:** "Technical Score" and "Final Score" are the **same number**.
> "Final Score **V2**" (§6) is the separate composite blend used for ranking.

---

## 2. Fundamental Score — `factor_scores.fundamental_score`

Starts at **50** (neutral), then adds/subtracts points by thresholding eight real
yfinance fundamentals. Returns `None` if none are present (e.g. a bank with no D/E).

| Metric | Good (+) | OK | Bad (−) | Points (good/ok/bad) |
|---|---|---|---|---|
| Revenue Growth % | ≥15 | ≥5 | <0 | +8 / +4 / −8 |
| EPS Growth % | ≥15 | ≥0 | <0 | +8 / +4 / −8 |
| FCF Growth % | ≥10 | ≥0 | <0 | +5 / 0 / −5 |
| Operating Margin % | ≥20 | ≥10 | <0 | +8 / +4 / −6 |
| Debt/Equity (lower better) | ≤0.5 | ≤1.0 | >2.0 | +6 / +3 / −6 |
| ROIC % | ≥15 | ≥8 | <0 | +10 / +5 / −5 |
| PEG (if >0) | ≤1 | ≤2 | >2 | +8 / +4 / −6 |
| Forward PE (if >0) | ≤20 | ≤35 | >35 | +4 / 0 / −6 |

```
Fundamental Score = clamp( 50 + Σ(metric points) , 0, 100 )
```

---

## 3. Sector Score — `market.sector_intelligence`

Computed **per sector** (11 SPDR sector ETFs vs `^GSPC`, one batched 1-year
download), then assigned to a stock by mapping its sector EN→HE
(`sector_score_for`). Three components:

| Component | Max pts | Rule |
|---|---|---|
| **Trend** (vs MAs) | 40 | Price>MA50>MA200 → 40 ("עולה"); Price>MA50 → 25 ("מתחזק"); mixed → 15; Price<MA50<MA200 → 0 ("יורד") |
| **Momentum** (1-month return, mapped −10%…+15%) | 30 | `momentum = clamp((ret_1m + 10)/25·100)`; pts = `momentum/100·30` |
| **Relative strength** vs S&P (1-month) | 30 | `rs_1m = ret_1m − spx_1m`; pts = `clamp((rs_1m + 8)/16·30, 0, 30)` |

```
Sector Score = clamp( trend_pts + momentum_pts + rs_pts , 0, 100 )   # ranked desc; rank 1 = strongest
```

---

## 4. News Score — `news/sentiment.py`

Transparent keyword lexicon (≈35 positive, ≈40 negative terms) over free Yahoo
headlines. For each headline, count positive/negative keyword hits:

```
total = pos + neg
News Score = 50                  if total == 0   (news exists but no clear tone, or no news)
           = round(100·pos/total) otherwise
```

50 = neutral. **Not deep NLP** — a deliberate, documented free-tier simplification.
Returns `{score, pos, neg, n}` so the UI can show *why*.

---

## 5. Risk Score — `risk.py::risk_score` (higher = riskier)

Weighted blend of three real metrics; weights **renormalize** over whatever is
available:

| Input | Weight | Normalization (→ 0–100) |
|---|---|---|
| Volatility (annualized %) | **45%** | `clamp((vol − 15)/(60 − 15)·100)` |
| Beta (vs S&P 500) | **25%** | `clamp((beta − 0.7)/(1.8 − 0.7)·100)` |
| Max Drawdown (abs %) | **30%** | `clamp((|mdd| − 15)/(60 − 15)·100)` |

```
Risk Score = round( weighted_average(parts, weights) )
```

Category: `<30 נמוך · <55 בינוני · <75 גבוה · ≥75 גבוה מאוד`.
(A simpler per-stock fallback `factor_scores.risk_score` exists for the watchlist
detail view; the `risk.py` version is authoritative and feeds the composite.)
Full risk methodology → `RISK_ENGINE.md`.

---

## 6. Final Score V2 (composite) — `composite.py::composite_score`

The ranking score. Weighted blend of five dimensions; **risk enters as health**
`100 − risk` so lower risk lifts the score.

### Target weights (Phase 14)

| Dimension | Weight |
|---|---|
| **Fundamental** | **35%** |
| **Technical** | **25%** |
| **Sector** | **20%** |
| **News** | **10%** |
| **Risk (health)** | **10%** |

### Missing-data handling (renormalization)

A stock is **never** zero-filled for missing data. Weights renormalize over the
**available** dimensions:

```
available = { dims with a real numeric value }
total_w   = Σ WEIGHTS[d]  for d in available
for each available dim d:
    eff_w[d]        = WEIGHTS[d] / total_w
    contribution[d] = dim_value · eff_w[d]
Final Score V2 = clamp( Σ contribution[d] , 0, 100 )
completeness   = total_w        # share of weight that had data (trust signal)
```

Returns `final`, per-dimension `contributions` (sum == final), effective
`weights`, `raw` inputs, `completeness`, and the `missing` list — **fully
decomposable** and surfaced in the UI as a contribution breakdown.

### Worked example (a bank, no fundamentals)

If Fundamental is missing, its 35% redistributes proportionally across
Technical/Sector/News/Risk (which together renormalize from 65% to 100%), and
`completeness = 0.65` is shown so the user knows the score rests on fewer pillars.

---

## 7. Supporting derived metrics

- **Expected Upside %** = `DistFromHigh% · (0.4 + 0.6·Score/100)` (0 if already at the high).
- **Confidence %** — from the backtest (sample size + win rate + OOS agreement); see `TRUST_VALIDATION.md`.
- **Opportunity classification** (`interpret.classify`): 🟢 *positive* if breakout
  OR (Price>MA200 AND Price>MA50 AND Score≥65); 🔴 *avoid* if Price<MA200 OR RSI<40
  OR Score<35; 🟡 *watch* otherwise.

---

## 8. Why this design

- **Fundamental-weighted (35%)** so the ranking is not momentum-only (the original
  MVP's main weakness). Verified impact: quality names rose materially
  (e.g. V 35→71, NVDA 33→68) after V2 replaced the momentum-only score.
- **Transparent + decomposable** — every score breaks into named contributions, so
  a reviewer can audit *why* a stock ranks where it does.
- **Graceful degradation** — renormalization + "אין נתון" instead of fake zeros.
