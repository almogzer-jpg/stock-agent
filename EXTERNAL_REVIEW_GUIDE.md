# EXTERNAL_REVIEW_GUIDE — Stock Agent Pro
Audience: external product / UX / technical / investment-quality reviewer (e.g. ChatGPT).
Package built: 12/07/2026. All 106 automated tests passing at packaging time.

## What this is
A Hebrew-first (RTL), free-data, institutional-style **Investment Decision Platform** built on
Python + Streamlit. Identity: "האנליסט השקוף" — every number real & reproducible, every
recommendation explained, missing data shown as "אין נתון זמין", never invented.
Read `PRODUCT_IDENTITY.md` (golden rules + quality gate), `DESIGN_SYSTEM.md` (HIG),
`INTELLIGENCE_ENGINE_V1.md` (analysis roadmap incl. E0 Decision Engine spec).

## Live app
- Streamlit Cloud: **<OWNER-FILLS-IN — the *.streamlit.app URL>** (desktop + mobile at `?m=1`)
- Local: `pip install -r requirements.txt` → `streamlit run dashboard/app.py`
  (Windows shortcut: `dashboard.bat`). Python 3.12. First artifact build: `python run.py`
  (~40s) + `python scanner.py ALL` (~2 min) — or just use the committed `data/` snapshot.
- Clean-install proof: `.github/workflows/refresh-data.yml` runs the full pipeline daily on a
  clean Ubuntu runner (pip install → run.py → scanner.py) and commits the snapshot — green runs
  = the app builds from scratch.

## Main files
- `dashboard/app.py` — desktop UI (7 pages) · `dashboard/mobile.py` — separate mobile app
  (bottom-nav) · `dashboard/theme.py` — design tokens/components · `dashboard/views.py` — pure
  presentation shaping.
- Engines: `ranking_engine/` (composite Score V2 + factors), `risk.py`, `technicals.py`
  (S/R, R/R, performance), `deepdive.py` (company report + investment decision),
  `proprietary.py` (labeled calculated indicators), `market.py` (regime/sectors),
  `globalmkt.py` (crypto/FX/commodities/rates), `backtesting/`, `alerts/`, `events.py`,
  `scanner.py` (500+ universe), `run.py` (pipeline → data/ artifacts).

## Navigation (desktop sidebar)
🏠 ראשי (Market Command Center: regime header → 15-asset global strip → capital flow →
opportunities table → hot stocks → macro+breadth → events/analyst updates → alerts → insight →
quick actions) · 🔎 ניתוח חברה (research-report header → Investment Decision card → performance
chips → charts → executive summary → financials/valuation → scores → technical+levels →
scenarios → final opinion; live yfinance, cached 30 min — the ONLY live-fetch page) ·
💎 הזדמנויות (filter form → sortable grid/cards toggle) · 🗺️ סקטורים (conclusion → heatmap →
intelligence table → per-sector drill-down) · 🚨 התראות (action center by severity) ·
📊 אינטליגנציית שוק (global markets 5 tabs + scored table + backtest) · ⚙️ הגדרות.
Mobile (`?m=1` or narrow screen): sticky bottom nav — בית/ניתוח/הזדמנויות/סקטורים/התראות/⚙️.

## Data sources & refresh
| Data | Source | Refresh |
|---|---|---|
| Prices/OHLCV, statements, analyst targets, holders | Yahoo Finance via `yfinance` (free) | Watchlist+universe: daily GitHub Action (04:00 UTC Mon-Fri) commits `data/` snapshot; deep-dive page: live, 30-min cache |
| Global (indices/crypto/FX/commodities/rates) | yfinance batch (`globalmkt.py`) | same daily Action |
| Sector strength | Sector SPDR ETFs vs ^GSPC | daily |
| News sentiment | RSS headlines + Hebrew lexicon scorer | daily (basic — known limitation) |
| Events (earnings, rating actions) | yfinance calendar/upgrades | daily |
Single-source dependency (Yahoo) is a known risk — fallback source is on the roadmap.

## Complete vs experimental
**Complete & verified:** design system + dark native theme; Score V2 composite (decomposable);
risk engine (β/vol/DD); support/resistance engine (volume-confirmed pivots, R/R, breakout
status, tested); performance engine (periods incl. tz-aware YTD fix, alpha vs S&P); investment
decision card (entry quality, checklist, matrix, price zones); scenario cards (analyst targets
+ labeled model likelihood); global markets; mobile app; alerts action center; auto data
refresh; WCAG-AA enforced by tests; 106 unit tests.
**Experimental / v0:** news sentiment (lexicon), backtester (single breakout signal,
small samples), "target price" on the home table (= our calculated upside expressed as price,
labeled), Hebrew auto-translation of company descriptions (Google Translate).

## Where we most want reviewer criticism
1. Investment-methodology soundness: Score V2 weights, entry-quality rules, R/R framing,
   scenario likelihood derivation (see honesty labels) — is anything misleading?
2. E0/E1-E7 roadmap (`INTELLIGENCE_ENGINE_V1.md`) — priorities and gaps.
3. Decision-language copy: is any conclusion stated stronger than the evidence?
4. UX: company page length; opportunities filter flow; anything still "dashboard-y".
5. Trust surface: as-of timestamps coverage, provenance, confidence gating.

## Known bugs & limitations (full list in KNOWN_LIMITATIONS.md inside the package)
Screenshots are NOT included in this package — the packaging environment cannot export browser
captures to files; use the live URL (all pages verified by DOM automation instead, results in
TEST_REPORT). Deep-dive page takes ~8-12s live fetch without a loading skeleton (roadmap item).
