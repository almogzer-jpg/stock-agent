# Sample Output — 💎 Top Opportunities

*Live snapshot from `data/results.csv` (top of the ranked watchlist) · 12/06/2026.*
Ranked by **Final Score V2**. Every column is real engine output.

| Ticker | Company | Status | Score V2 | Tech | Fund | Sector | Risk | Trust | Risk Lvl | β | Vol% | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **LLY** | Eli Lilly | 🟢 מגמה חזקה | **78** | 78 | 93 | 13.4* | 29 | 55 | נמוך | 0.53 | 38.0 | גבוה |
| **JPM** | JP Morgan | 🟢 מגמה חזקה | **76** | 76 | 73 | 13.2* | 13 | 75 | נמוך | 0.94 | 21.8 | גבוה |
| **AMD** | Adv. Micro Devices | 🟢 מגמה חזקה | **74** | 74 | 79 | 16.2* | 79 | 60 | גבוה מאוד | 2.88 | 66.7 | גבוה |
| **V** | Visa | 🔴 להימנעות | **74** | 35 | 96 | 13.2* | 11 | 49 | נמוך | 0.53 | 22.3 | בינוני |
| **PG** | Procter & Gamble | 🟡 למעקב | **73** | 62 | 68 | 14.2* | 4 | 57 | נמוך | −0.01 | 18.8 | גבוה |

\* the Sector column shows the **sector contribution to Score V2** (weighted points), not the raw 0–100 sector score.

### Worked decomposition — LLY (Score V2 = 78)

Contributions (sum to the final score): Fundamental **32.5** + Technical **19.5** +
Sector **13.4** + News **5.0** + Risk-health **7.1** = **77.5 → 78**.
Completeness 100%. This is the exact breakdown the dashboard renders as
contribution bars.

### Note on V (Visa)

Visa shows Score V2 74 (fundamentally excellent: 96) **but** is classified 🔴
"avoid" because its **technical** score is only 35 (below MA-trend / weak
momentum). This is the system working as designed — the composite rewards quality,
while the classification layer (`interpret.classify`) still warns that *price
action* is currently negative. A reviewer sees both signals, not a single blended
verdict that hides the conflict.
