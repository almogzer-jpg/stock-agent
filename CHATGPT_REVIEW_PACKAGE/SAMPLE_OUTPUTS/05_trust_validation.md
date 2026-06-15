# Sample Output — 🛡️ Trust & Validation

*Live snapshot from `data/system_health.json` + trust columns in `data/results.csv`
· 15/06/2026.*

## System Health (data foundation)

| Metric | Value |
|---|---|
| Stocks scanned | 20 |
| Breakout signals today | 0 |
| **Data completeness** | **100.0%** |
| Failed data pulls | 0 |
| Average confidence | 53.9 |
| **Average trust** | **57.9** |

**Sector distribution (scanned):** Technology 7 · Financial Services 3 ·
Communication Services 3 · Consumer Cyclical 3 · Healthcare 2 · Consumer Defensive 2.

## Per-stock Trust Scores

| Ticker | Trust | Category | Confidence | Notes |
|---|---|---|---|---|
| JPM | **75** | גבוה | 83% | full risk model + complete fundamentals |
| AMD | 60 | בינוני | 77% | high confidence but very-high risk caps trust |
| PG | 57 | בינוני | 66% | mixed signals |
| LLY | 55 | בינוני | 76% | strong fundamentals, moderate sample |
| V | 49 | בינוני | 48% | technical/fundamental conflict lowers consistency |

## How a Trust Score is built (JPM = 75)

Seven weighted factors (weights sum to 100):
data quality (15) + historical validation (20) + sample size (15) +
out-of-sample (15) + fundamental completeness (10) + score consistency (15) +
risk model (10). Each scaled 0–1, multiplied by its weight, summed.

## Why trust / why be cautious (example)
- ✅ "מודל סיכון מלא (ביתא/תנודתיות/Drawdown)"
- ✅ "נתונים פונדמנטליים מלאים"
- ⚠️ "ללא אימות Out-of-Sample" (for names with too few historical signals)
- ⚠️ "אותות סותרים (טכני מול פונדמנטלי)" (e.g. Visa: fund 96 vs tech 35)

The system is **skeptical by construction**: small samples and missing
out-of-sample validation actively *lower* trust rather than being ignored.
