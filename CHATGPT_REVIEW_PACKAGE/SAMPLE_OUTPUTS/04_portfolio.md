# Sample Output — 💼 Portfolio & 🧭 Decisions

*Live snapshot from `data/portfolio.json` · 15/06/2026.* (Holdings are sample data
in `portfolio.csv`; the analytics/decisions are real engine output.)

## Summary

| Metric | Value |
|---|---|
| Total value | **$28,561.35** |
| Total P/L | **+$6,311.35 (+28.37%)** |
| Daily change | −0.13% (vs S&P +0.50%) |
| 1-month | +1.34% (vs S&P +0.41%) |
| **Health score** | **54 / 100** |

## Holdings

| Ticker | Weight | Mkt Value | P/L % | Score V2 | Risk | β | Status |
|---|---|---|---|---|---|---|---|
| NVDA | **28.74%** | $8,207.60 | +36.79% | 70 | בינוני | 1.82 | 🔴 avoid |
| JPM | 22.46% | $6,414.40 | +28.29% | 76 | נמוך | 0.94 | 🟢 positive |
| LLY | 19.83% | $5,665.00 | +38.17% | 78 | נמוך | 0.53 | 🟢 positive |
| AAPL | 15.29% | $4,366.95 | +38.63% | 63 | נמוך | 0.89 | 🟡 watch |
| MSFT | 13.68% | $3,907.40 | −2.32% | 65 | נמוך | 0.83 | 🔴 avoid |

## Risk & Concentration

| Metric | Value |
|---|---|
| Weighted beta | 1.09 |
| Weighted volatility | 29.4% |
| Effective positions (1/HHI) | 4.7 |
| Max position | 28.7% (NVDA) |
| Max sector | 57.7% (Technology) |
| **Concentration risk** | **51 / 100** |

**Exposures:** Technology 57.7% · Financial Services 22.5% · Healthcare 19.8%.
**Correlation:** no high pairs (max ≈ 0.37 NVDA–MSFT).

## Hard constraint warnings
- ⚠️ פוזיציה בודדת: NVDA 29% (> 20%)
- ⚠️ פוזיציה בודדת: JPM 22% (> 20%)
- ⚠️ סקטור Technology 58% (> 35%)

## 🧭 What to do today (Decision Engine)
- 🟡 הקטן **NVDA** ל‑10% (כעת 28.7%) — *priority: גבוהה; β 1.82, position >20%*
- 🟡 הקטן **JPM** ל‑15% (כעת 22.5%) — *priority: גבוהה; position >20%*
- 🟡 הקטן **AAPL** ל‑5% (כעת 15.3%) — *valuation only 20*
- 🟡 הקטן **LLY** ל‑15% (כעת 19.8%)
- הקטן חשיפה ל‑Technology (כעת 57.7%, מעל מגבלת 35%)
- שקול הגדלת חשיפה ל‑Real Estate (סקטור חזק, ציון 75, כעת 0%) · Industrials (ציון 72, כעת 0%)

Each action traces to: target-allocation bucket (from Score V2), risk-category cap,
sector strength, and concentration constraints — fully explained per holding.
