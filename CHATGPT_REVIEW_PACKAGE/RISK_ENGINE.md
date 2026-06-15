# RISK_ENGINE.md — Risk Intelligence Engine

Source: `risk.py` (per-stock + portfolio risk). Pure functions over pandas price
series, unit-tested in `tests/test_risk.py` (49 test statements). All metrics from
**real price history** (2 years of daily closes); `^GSPC` is the market proxy.

---

## 1. Beta — `beta(stock_close, market_close, window=252)`

Sensitivity to the market over the trailing ~1 year (252 trading days).

```
r_s = daily returns of the stock     (pct_change, NaN-dropped)
r_m = daily returns of ^GSPC
align r_s, r_m on common dates (inner join), keep last 252
Beta = Cov(r_s, r_m) / Var(r_m)
```

- Requires ≥30 aligned observations, else `None`.
- `Var(r_m) ≤ 0` → `None` (guard).
- Rounded to 2 decimals.
- **Interpretation:** β=1 moves with the market; β>1.3 flagged as "sensitive to
  market swings."

---

## 2. Volatility — `volatility(close, window=252)`

Annualized standard deviation of daily returns, in percent.

```
r = daily returns (last 252)
Volatility % = std(r) · √252 · 100
```

- Requires ≥20 returns, else `None`. Rounded to 1 decimal.
- **Interpretation:** ~15% calm, ~45%+ high (warning), ~60%+ extreme.

---

## 3. Max Drawdown — `max_drawdown(close, window=252)`

Largest peak-to-trough decline over the window (negative %).

```
s  = last 252 closes
dd = s / cummax(s) − 1          # running drawdown from the highest prior peak
Max Drawdown % = min(dd) · 100  # most negative point
```

- Requires ≥20 points, else `None`. Rounded to 1 decimal.
- **Interpretation:** worse than −35% flagged as "deep historical drawdown."

---

## 4. Risk Score (per-stock) — `risk_score(vol, beta, mdd)`

Combines the three metrics into 0–100 (**higher = riskier**). Each input is
normalized to 0–100, then a **weighted average** is taken over whatever inputs
exist (weights renormalize if one is missing):

| Input | Weight | Normalization |
|---|---|---|
| Volatility | **45%** | `clamp((vol − 15)/45 · 100)` |
| Beta | **25%** | `clamp((beta − 0.7)/1.1 · 100)` |
| Max Drawdown (abs) | **30%** | `clamp((|mdd| − 15)/45 · 100)` |

```
Risk Score = round( numpy.average(parts, weights) )      # None if no inputs
```

**Category** (`category()`):

| Score | Category |
|---|---|
| < 30 | נמוך (Low) |
| 30–54 | בינוני (Medium) |
| 55–74 | גבוה (High) |
| ≥ 75 | גבוה מאוד (Very High) |

**Per-stock warnings** (`risk_profile`): β>1.3, vol>45%, maxDD<−35% each emit a
human-readable Hebrew warning. Verified examples: AMD β2.88 / vol67 → "גבוה מאוד";
PG β≈−0.01 → "נמוך".

This Risk Score **overrides** the simpler watchlist risk and feeds Final Score V2
as `risk health = 100 − risk` (10% weight).

---

## 5. Correlation — `correlation_pairs(closes_map, threshold=0.7)`

Detects *hidden concentration*: holdings that look diversified by name but move
together.

```
For each holding: daily returns (NaN-dropped)
Build a returns DataFrame across all holdings, drop NaN rows (need ≥30 common days)
corr  = returns.corr()                      # Pearson, rounded to 2dp
matrix = full {ticker: {ticker: corr}}
high_pairs = all pairs with |corr| ≥ 0.7    # sorted by |corr| desc
```

Each high pair becomes a portfolio warning ("קורלציה גבוהה A–B … ריכוז סמוי").

---

## 6. Portfolio Risk — `portfolio_risk(positions, betas, vols, sector_exposure)`

Aggregates per-holding risk to the portfolio level.

**Weighted exposures** (weights = position % / 100):
```
Weighted Beta        = Σ wᵢ · βᵢ
Weighted Volatility  = Σ wᵢ · volᵢ
```

**Diversification (Herfindahl):**
```
HHI                  = Σ wᵢ²
Effective positions  = 1 / HHI          # "how many equal-weight names this really is"
```

**Concentration Risk (0–100, higher = more concentrated):**
```
conc = clamp( (max_position% − 20)/30 · 50  +  (max_sector% − 25)/45 · 50 )
```

**Portfolio warnings:**

| Trigger | Warning |
|---|---|
| max single position > 25% | "פוזיציה בודדת גדולה: X%" |
| max sector exposure > 40% | "ריכוז סקטוריאלי גבוה: X%" |
| effective positions < 4 | "פיזור נמוך: X פוזיציות אפקטיביות" |
| weighted beta > 1.2 | "ביתא תיק גבוהה — רגישות גבוהה לשוק" |

Verified example (sample over-concentrated portfolio): weighted β≈1.09,
concentration≈51, NVDA flagged at 29% (>25%), Technology flagged at 58% (>40%).

---

## 7. How risk drives decisions

The Risk Category **caps position size** in the Decision Engine
(`decisions.target_allocation`): "גבוה מאוד" caps at 5%, "גבוה" caps at 10%.
Portfolio-level warnings and high-correlation pairs become **hard constraint
warnings** and "what to do today" risk-reduction actions
(see `OPPORTUNITY_HUNTER.md` / `DASHBOARD_WALKTHROUGH.md`).

---

## 8. Limitations (be explicit)

- **Price-history only** — no fundamental/macro factor model; beta is single-factor
  vs `^GSPC`.
- **Backward-looking** — volatility/drawdown/beta describe the past 252 days; regime
  shifts aren't predicted.
- **252-day window** — recent structural changes (e.g. a recent IPO or spin-off) may
  have too little history (`None` returned, surfaced as "אין נתון").
- **Correlation needs ≥30 common days** across holdings; sparse/young holdings are
  excluded from the matrix.
