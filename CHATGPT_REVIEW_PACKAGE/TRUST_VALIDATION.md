# TRUST_VALIDATION.md — Trust, Confidence & Backtesting

Sources: `trust.py` (trust score + signal reliability) and
`backtesting/backtester.py` (signal backtest + out-of-sample split).
Answers the question: **"How much should I trust this recommendation?"**

---

## 1. Trust Score — `trust.trust_score(row, backtest)`

A 0–100 score from **seven real factors** (weights sum to 100). Each factor is
scored to a 0–1 sub-value, multiplied by its weight, and summed.

| Factor | Weight | Sub-value (0–1) |
|---|---|---|
| **Data quality** | 15 | 0.5 baseline + 0.5 if a Fundamental Score exists |
| **Historical validation** | 20 | `band(win_rate, 40→70)` if win_rate present **and** occurrences ≥4; else 0.2 |
| **Sample size** | 15 | `band(occurrences, 2→10)` |
| **Out-of-sample** | 15 | `band(oos_win_rate, 40→70)` if present; else 0.3 |
| **Fundamental completeness** | 10 | fraction of the 8 fundamental fields present |
| **Score consistency** | 15 | `0.5·(Completeness/100) + 0.5·consistency` |
| **Risk model** | 10 | 1.0 if Beta+Volatility+MaxDrawdown all present; else 0.3 |

Where:
- `band(x, lo, hi) = clamp((x − lo)/(hi − lo), 0, 1)` — a linear ramp.
- `consistency = 1 − min(1, (max − min)/100)` over the available sub-scores
  (Technical / Fundamental / Sentiment); ≥2 needed, else 0.5. High = the signals
  agree; low = technical and fundamental disagree.

```
factors[k]  = round( WEIGHTS[k] · sub[k] , 1 )
Trust Score = round( clamp( Σ factors[k] , 0, 100 ) )
```

**Category:** `≥66 גבוה · 40–65 בינוני · <40 נמוך`.

**Strengths / limitations** are generated explicitly, e.g.:
- ✅ "אומת היסטורית: 70% הצלחה על 12 מופעים" (occ≥8 and win_rate≥55)
- ✅ "ביצועי Out-of-Sample עקביים (65%)" (oos≥50)
- ⚠️ "מדגם היסטורי קטן (3 מופעים)" / "אין מספיק איתותים היסטוריים לאימות"
- ⚠️ "ללא אימות Out-of-Sample" / "אותות סותרים (טכני מול פונדמנטלי)"

Unit-tested invariants (`tests/test_trust.py`): factor points sum to the score
(±1); strong validation always beats weak; missing fundamentals are flagged and
cap the score below 80.

---

## 2. Confidence calculations

Two related notions:

### a) Backtest Confidence (`backtester.backtest_signal`)
A categorical label from sample size + win rate + OOS agreement:

| Condition | Confidence |
|---|---|
| occ ≥ 8 **and** win_rate ≥ 60 **and** (oos_win_rate ≥ 50 or None) | **גבוה (High)** |
| occ ≥ 4 **and** win_rate ≥ 50 | **בינוני (Medium)** |
| otherwise | **נמוך (Low)** |

### b) Signal Reliability (`trust.signal_reliability`)
A bundle for one recommendation: `confidence` (the stock's Confidence %),
category, historical win rate, occurrences, average return, **excess return vs
S&P 500** (`benchmark_rel`), and max drawdown — everything a user needs to judge
the edge.

### c) Decision Confidence (`decisions.decide_holding`)
For a portfolio action: `0.6·holding_confidence + 0.4·action_clarity`, where
clarity scales with the size of the gap between current and target weight.

---

## 3. Historical success methodology — `backtest_signal`

Backtests the **breakout signal** on one ticker's full 2-year history. Requires
≥260 rows, else `None`.

**Signal definition** (same as the live scanner):
```
Close > MA50  AND  Close > MA200  AND  DistFromHigh% ≤ 10
AND  Volume ≥ 1.5 × 20-day avg volume
AND  50 ≤ RSI(14) ≤ 75
```

**Trade simulation (non-overlapping):**
1. Walk forward; when the signal is true, **enter** at that close.
2. **Exit** on the first close **below MA50** (trend break) or after `max_hold=20`
   trading days, whichever comes first.
3. Record return %, intra-trade drawdown, holding days, and benchmark-relative
   return (`ret − ^GSPC return over the same window`, via `asof` alignment).
4. Resume scanning **after** the exit (no overlapping trades).

**Aggregate stats** (`_agg`): occurrences, win rate (% of trades >0), average &
median return, worst-trade drawdown, mean benchmark-relative return, average
holding period.

Verified examples: GOOGL 66.7% win / +4.23% avg / +4.0 vs benchmark;
META 20% / −5.09% → Low confidence; TSLA 0 occurrences → `None`.

---

## 4. Out-of-sample (OOS) methodology

To guard against in-sample overfitting, trades are split **70/30 by time**:

```
split  = floor( len(trades) · 0.7 )
IS     = trades[:split]      # in-sample (older 70%)
OOS    = trades[split:]      # out-of-sample (most recent 30%)
out["is_win_rate"]   = win_rate(IS)
out["oos_win_rate"]  = win_rate(OOS)
out["oos_avg_return"]= avg_return(OOS)
```

OOS win rate then feeds **both** the Confidence label (§2a) and the Trust Score's
"out-of-sample" factor (§1). If a name has 0 occurrences, OOS is `None` and trust
explicitly says "ללא אימות Out-of-Sample."

**Why this matters:** a signal that wins in-sample but degrades on the most recent
30% gets downgraded — the system is skeptical of its own edge by construction.

---

## 5. System Health — `data/system_health.json`

A pipeline-wide validation snapshot written every run: number scanned, signals,
data completeness, failed pulls, average confidence, average trust, sector
distribution. Surfaced as KPIs on the **🛡️ אמון ואימות** tab so the user can see
the *data foundation's* health, not just per-stock scores.

---

## 6. Honest limitations

- **No costs/slippage/taxes/sizing** — the backtest measures raw signal edge, not
  net realizable P&L.
- **Small samples** — many names have few or zero historical signals; trust
  correctly falls back to low/None rather than inventing confidence.
- **One signal** — only the breakout setup is backtested; other score components
  aren't independently validated historically.
- **Survivorship** — the universe is *today's* constituents; delisted names aren't
  in the historical sample.
