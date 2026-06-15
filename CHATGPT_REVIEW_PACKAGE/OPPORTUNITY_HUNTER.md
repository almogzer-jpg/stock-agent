# OPPORTUNITY_HUNTER.md — Market-Wide Discovery Engine

Source: `scanner.py` + `universe.py` (+ `market.py`, `risk.py`, `decisions.py`,
`composite.py`, `fundamentals/`, `backtester.py`). Produces `data/universe.json`,
which powers the dashboard's **🔭 סורק שוק (Market Scanner)** tab.

---

## 1. Universe scanned — `universe.py`

| Universe | Source | Size |
|---|---|---|
| **S&P 500** | Wikipedia constituent table | ~503 |
| **Nasdaq-100** | Wikipedia constituent table | ~101 |
| **ALL** (default) | De-duplicated **union** of the two | **~500–514 large/mid-cap US names** |
| RUSSELL2000 | Documented hook, returns `[]` | — (excluded, see below) |

- Fetched with a browser `User-Agent` (Wikipedia blocks default agents) →
  `pandas.read_html`. Tickers normalized (`.`→`-`, upper-cased).
- **Cached weekly** to `data/universe_tickers.json` (TTL 7 days) — constituents
  change rarely.
- **Fallback:** on any fetch failure, falls back to the local `watchlist.txt` so
  the pipeline never hard-fails.
- **Russell 2000 intentionally excluded** — no clean free constituent table at
  scale, and 2,000 small-caps can't be scanned in <5 min on free data. Architect's
  call: *scan quality over raw breadth.* This is a stated limitation, not an
  oversight.

---

## 2. Two-phase scan — `scan_universe()`

The key to scanning ~500 names in **~95 seconds** on free data: do cheap work for
everyone, expensive work only for the leaders.

### Phase A — cheap, ALL tickers (vectorized, price-only)
- One **batched** `yf.download` (2y, chunks of 80, threaded) → `{ticker: OHLCV}`.
- Per ticker (needs ≥210 closes): MA20/50/200, RSI(14), 52-week high &
  `DistFromHigh%`, daily change, 1-month & 3-month returns, volume ratio.
- **Technical Score** (`score_stock`), **breakout** flag, and a full **risk
  profile** (beta/vol/maxDD → Risk Score + category) — all from prices.
- Sort the whole universe by Technical Score.

### Phase B — deep, **top-40 only** (`SCAN_TOP_ENRICH=40`)
For the 40 highest Technical Scores, add:
- **Fundamentals** (weekly-cached) → Fundamental Score + sector + market cap.
- **Valuation Score** (`decisions.valuation_score`, from PEG + Forward PE).
- **Sector Score** (from `market.sector_intelligence`).
- **Final Score V2** (`composite_score`, with `news=50` placeholder in the scan).
- **Signal backtest** (`backtest_signal`) → historical win rate + Confidence.
- **Discovery tags** (see §4).

> **Material limitation:** because only the top-40-by-technical are enriched,
> rankings that need fundamentals/valuation (`undervalued`, `high_quality`) are
> drawn from that enriched subset — i.e. *"cheap/quality **among the technically
> strong**,"* not the whole-universe cheapest. `momentum` is the exception
> (computed over the **entire** universe).

---

## 3. Categories (5 rankings)

`data/universe.json → rankings`:

| Ranking | Key | Pool | Meaning |
|---|---|---|---|
| **opportunities** | top by `ScoreV2` | enriched (40) | Best overall composite |
| **undervalued** | top by `Valuation` | enriched (40) | Best value (PEG/Fwd PE) among the strong |
| **momentum** | top by `Ret3m` | **whole universe** | Strongest 3-month price momentum |
| **high_quality** | top by `ScoreFundamental` | enriched (40) | Best fundamentals |
| **turnarounds** | tagged "תפנית" by `ScoreV2` | enriched (40) | Reclaimed key MAs after weakness |

---

## 4. Discovery tags (per enriched name)

Assigned in Phase B; surfaced as chips in the UI:

| Tag (HE) | Condition |
|---|---|
| פריצה (Breakout) | breakout setup true |
| מומנטום חזק (Strong momentum) | `Ret3m ≥ 15%` **and** Price > MA50 |
| מוערך בחסר (Undervalued) | `Valuation ≥ 65` |
| איכות גבוהה (High quality) | `ScoreFundamental ≥ 70` |
| האצת רווחים (Earnings accel.) | `EPSGrowth ≥ 20%` |
| תפנית (Turnaround) | was below 200-MA in last 60d, now > MA50 **and** > MA200 |
| רוטציה סקטוריאלית (Sector rotation) | `SectorScore ≥ 70` |
| הזדמנות בביטחון גבוה (High-confidence) | `ScoreV2 ≥ 70` **and** Confidence ≠ low |

---

## 5. Ranking logic

1. **Phase A** ranks the entire universe by Technical Score (momentum/trend quality).
2. **Phase B** recomputes the top-40 with **Final Score V2** (fundamental-weighted),
   which re-orders them toward quality/value, not just momentum.
3. Each ranking is the top-N (default 10) of its pool by its key metric, filtering
   out `None` values.
4. The dashboard additionally offers **interactive filters**: sector, market-cap,
   min score, risk level, valuation, momentum, quality.

---

## 6. Filters (dashboard `🔭 סורק שוק`)

The full universe (`universe.json → all`) is filterable by:
- **Sector** (from enriched fundamentals)
- **Market cap** bucket
- **Min Final Score V2**
- **Risk level** (נמוך…גבוה מאוד)
- **Valuation** / **Momentum** / **Quality** thresholds

Top-10 ranking columns + a sector-distribution chart sit above the filterable
opportunities table.

---

## 7. Historical validation

Every enriched opportunity carries a **historical win rate** and a **Confidence**
level from the signal backtest (`backtest_signal`) — see `TRUST_VALIDATION.md` for
the full backtest + OOS methodology. The "high-confidence opportunity" tag
requires `ScoreV2 ≥ 70` **and** a non-low Confidence, so the headline list is
biased toward statistically-supported setups.

**Verified run:** full `ALL` scan of 514 names in ~95 s (target <5 min). Example
output — momentum: ARM/MRVL/INTC; opportunities: value/financial names
(DOV/TRV/AFL) surfaced because ScoreV2 weights fundamentals.

---

## 8. Limitations recap

- Top-40 enrichment cap (quality > breadth).
- Russell 2000 excluded.
- News set to neutral (50) inside the universe scan (news is fetched per-name only
  in the watchlist pipeline, not the 500-name scan, for speed).
- Backtest samples small for many names.
