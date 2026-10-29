# Research — evidence behind the verdict engine

Rule 17 of `PRODUCT_IDENTITY.md`: a rule may change a verdict only with historical
support. This folder holds the studies that decide which rules qualify.

## timing_study.py

**Question.** For stocks the system already likes, do the "wait" rules the app used
to apply (RSI overbought, price right under resistance, poor reward/risk to the
nearest levels, waiting for a pullback to support, long-term downtrend) predict
worse 3-month outcomes? Does the technical score (25% of Score V2) and the breakout
signal carry information?

**Method.**
- Universe: current S&P 500 members (`data/universe.json`), daily adjusted closes
  from Yahoo, 2014 → today. One sample every 21 trading days per ticker.
- Features use only data up to the sample date and the app's own functions
  (`technicals.sr_levels`, `ranking_engine.score.score_stock`,
  `scanners.breakout.is_breakout`, RSI-14, MA50/MA200). No look-ahead.
- Outcome: 63-trading-day return in excess of SPY, the deepest drawdown inside
  those 63 days, and the 10th-percentile return.
- Statistics are averaged per sample date first, then across dates; the ± column
  is the standard error across dates. A difference is called significant only
  when it exceeds twice the combined standard error.
- **Bias.** Survivorship: only today's members are sampled, which inflates absolute
  returns (and especially flatters stocks that were falling, since the ones that
  kept falling left the index). Read the study as a comparison between groups, not
  as an absolute return forecast.

**Results (first run, 29/10/2026: 499 tickers, 66,625 samples, 2015-2026).**

| Rule ("wait / avoid when…") | Group | Comparison | Conclusion |
|---|---|---|---|
| RSI ≥ 75 (uptrend) | +7.5% ±1.9 | RSI 50-70: +3.5% ±0.7 | Not supported (if anything, better) |
| Price ≤ 2% under resistance | +2.0% ±0.8 | > 2% under: +4.0% ±0.8 | Not significant, equal medians |
| Reward/risk < 1 | +3.8% ±0.8 | R/R ≥ 2: +2.4% ±1.2 | Not supported |
| Wait for a pullback to support | within 3% of support: +0.9% ±0.9 | > 8% above: +6.0% ±0.9 | Refuted (waiting did worse) |
| Below the 200-day average | +4.1% ±0.8 | uptrend: +4.5% ±0.7 | Return difference not significant; deeper drawdowns (−12.5% vs −11.3%) and worse 10th percentile (−14.3% vs −13.1%) |

**Decisions taken in `verdict.py`.**
- None of the timing rules gates the verdict (`TIMING_EVIDENCE`, all inactive, each
  with its finding). Price position is shown as information only
  (`deepdive.ENTRY_NOTE`).
- Trend stays, as a risk rule: below the 200-day average a non-strong company is
  "avoid" and a strong one is "wait".
- RSI ≥ 75 is disclosed as a volatility caution (slightly fatter left tail), never
  as a reason to wait.
- The setup base rates (`setups`: trend × RSI band, n ≥ 300) feed the "what happened
  before in similar situations" card, framed as interim drawdown and tail risk.

**Not testable with free data.** The fundamental score (35% of Score V2) and
valuation inputs need point-in-time fundamentals, which free sources do not
provide. Those weights remain an explicit, documented model choice, not a
validated forecast. Analyst price targets are shown as external consensus,
labeled, never as the system's forecast.

**Reproduce.**

```bash
python research/timing_study.py
```

Set `STUDY_SAMPLES_CSV=<path>` to keep the raw samples, and recompute the tables
without downloading again:

```bash
python research/timing_study.py --from-csv <path>
```
