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
- Statistics are averaged per sample date first, then across dates. The ± column
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
| Below the 200-day average | +4.1% ±0.8 | uptrend: +4.5% ±0.7 | Return difference not significant. Deeper drawdowns (−12.5% vs −11.3%) and worse 10th percentile (−14.3% vs −13.1%) |

**Model check: the technical score and the breakout signal (second run, same samples).**

| Group | 3-month excess | Avg. interim drawdown | n |
|---|---|---|---|
| Technical score 0-35 | +5.5% ±0.9 | −12.6% | 16,378 |
| Technical score 35-50 | +3.0% ±1.0 | −11.5% | 12,034 |
| Technical score 50-65 | +3.5% ±1.0 | −11.9% | 10,874 |
| Technical score 65-80 | +4.5% ±1.0 | −10.3% | 16,348 |
| Technical score 80-100 | +3.6% ±1.0 | −10.4% | 10,991 |
| Breakout signal (app definition) | +2.5% ±1.1 | −9.1% | 1,827 |
| No breakout signal | +5.1% ±0.6 | −12.0% | 64,798 |

Reading: the technical score (25% of Score V2) shows no monotonic link to 3-month excess
return, but higher scores came with shallower interim drawdowns, so it behaves as a risk
measure rather than a return predictor. The breakout signal underperformed the rest of the
sample by about 2.6 points (≈2.1 combined standard errors). Survivorship bias flatters the weak
groups, so this is evidence, not proof. **No weights were changed**: Score V2 is the product's
investment model and a change belongs to the owner's decision (see V4 approval notes).

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

## signal_study.py — is the technical score or the breakout signal a reason to buy?

Run on 01/11/2026: 499 tickers, 65,130 samples, 2015-2026, 1,800 breakout events.

**Method.** Per-date Spearman rank correlation (IC) between the signal and forward returns,
and the top-minus-bottom quintile spread, at 21, 63 and 126 trading days. Primary benchmark:
the equal-weight cross-section of the same date (removes the market and most of the survivorship
level bias). Secondary: the stock's SPDR sector ETF. Newey-West standard errors for the
overlapping horizons. Stability across 2015-2018, 2019-2022, 2023-2026 and across market regimes
(SPY above or below its 200-day average). Returns winsorised at 1%/99%. The breakout signal is
also compared with a matched control: stocks meeting every breakout condition except the
volume spike.

**Technical score (25% of Score V2).**

| Horizon | IC vs equal-weight (t) | Top − bottom quintile (t) | IC vs sector ETF (t) |
|---|---|---|---|
| 21 days | −0.014 (−1.1) | −0.45% (−1.7) | −0.007 (−0.6) |
| 63 days | −0.019 (−1.4) | −0.99% (−1.9) | −0.009 (−0.7) |
| 126 days | −0.015 (−0.9) | −1.32% (−1.4) | −0.008 (−0.5) |

- No period shows a stable positive link. 2019-2022 is negative (t −2.1 to −2.9), 2023-2026 is
  positive at 126 days (t 2.5). The sign flips, so there is no reliable return signal.
- After market declines (SPY below its 200-day average) the link is clearly negative
  (t −2.6 at 63 days, −3.9 at 126 days): high technical scores were followed by weaker
  returns, the "momentum crash" pattern known from the literature.
- Risk: higher scores came with shallower interim drawdowns (lowest quintile −9.7%, highest
  −8.2% over 63 days). The score describes trend and risk, not expected return.

**Breakout signal.**

| Horizon | vs all stocks same date (t) | vs matched control without volume spike (t) | vs sector ETF (t) |
|---|---|---|---|
| 21 days | −0.41% (−1.3) | −0.13% (−0.4) | +0.16% (1.1) |
| 63 days | −1.22% (−2.5) | −0.55% (−1.1) | +0.47% (1.6) |
| 126 days | −1.66% (−1.9) | −0.41% (−0.6) | +0.92% (2.0) |

The volume spike adds nothing over the matched control, the signal trails the equal-weight
cross-section, and results change sign across sub-periods. **Conclusion: no evidence that the
breakout signal is a buy signal.** Per the owner's decision (01/11/2026) it is shown as technical
information only, never as a standalone buying opportunity.

**Bias that remains.** Stocks that left the index are missing. That flatters weak stocks
(low technical scores) and therefore pushes the IC down. The honest reading is "no evidence of
positive predictive power", not "proven negative".

**Not changed.** Score V2 weights stay as they are. A weight change would need a test of the whole
V2 score, which requires point-in-time fundamentals that free sources do not provide. Options
for the owner are listed in the V4 approval notes.

## decision_structure_study.py — five dimensions instead of one mixed score (01/11/2026)

Shadow comparison on the 57 stocks with full fundamentals. Inputs: the canonical rows
(technicals from the 29/10/2026 close) and `decision_structure_inputs.json` (fundamentals,
analyst targets and price fetched from Yahoo on 01/11/2026). Nothing in the live engine changes.

- What orders Score V2 (rank correlation): fundamental −0.05, technical 0.58, sector 0.55,
  risk −0.45. A business-only quality score (fundamental_score without PEG / forward P/E)
  correlates 0.03 with Score V2, and only 4 of the top 10 overlap.
- Lowering the technical weight alone barely changes the ranking (10%: ρ 0.97, 0%: ρ 0.86),
  because sector momentum and price-derived risk still dominate.
- Price never enters the live verdict: 8 of the 40 live "buy" verdicts are above the analyst
  consensus target (AMGN, AWK, BDX, CHD, EXPD, LLY, MO, REGN).
- Proposed structure (quality from business data, price, timing, risk, one decision table):
  buy / wait / avoid 19 / 35 / 3 against 40 / 10 / 7 live. 37 of 57 verdicts change.

Owner-facing recommendation and decision table: `DECISION_ENGINE_PROPOSAL.md`.

## shadow_eval.py — outcomes of the four-dimension engine vs the live engine

Approved by the owner on 01/11/2026 (version A, see `DECISION_ENGINE_PROPOSAL.md`). `verdict4.py`
runs in shadow mode after every scan (`shadow.py`) and logs both engines' decisions with the
day's price to `data/shadow_log.jsonl`. This script measures excess return after 21 and 63
trading days (vs the equal-weight average of logged stocks that day and vs SPY), hit rate and
the worst drop inside the window, per engine and action, plus the disagreement cohorts.
Standard errors are clustered by day. Overlapping windows mean neighbouring days are not
independent, so even day-clustered errors overstate precision. No conclusion is printed for a
group with fewer than 20 decision days. Fewer buys is not a quality measure: the test is whether
the new engine's buys beat its own waits and avoids and the live buys, with shallower drawdowns.
