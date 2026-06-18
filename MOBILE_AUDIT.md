# MOBILE_AUDIT.md — Desktop→Mobile Adaptation Audit

Status: **approved**. Route chosen: **A — expand `dashboard/mobile.py`** (desktop `app.py` untouched).

## Architecture (critical)
Two separate UI codebases: **Desktop** = `dashboard/app.py` (7 pages); **Mobile** =
`dashboard/mobile.py` (separate, rendered when `?m=1`/narrow via `_is_mobile()` +
`st.stop()`). Desktop pages are **not** shown on phones — mobile gets only what
`mobile.py` renders.

## Navigation
**Desktop sidebar radio (7):** 🏠 ראשי · 🔎 ניתוח חברה · 💎 הזדמנויות · 🗺️ סקטורים ·
🚨 התראות · 📊 אינטליגנציית שוק · ⚙️ הגדרות. + sidebar: stock-count caption,
"📱 תצוגת מובייל", "🔄 רענן נתונים". Top bar: brand + status pill + date. No submenus.
**Mobile tabs (4):** 🏠 בית · 💎 הזדמנויות · 🗺️ סקטורים · 🔔 התראות + "🖥️ עבור לתצוגת מחשב".

## Screens (desktop)
- **🏠 ראשי:** 6 KPI · regime gauge + factor chips · S&P 6m chart · "הזדמנויות לבחינה היום" (3) · markets strip · Top3/5/10 opp cards (sparkline+6 score bars) · method expander.
- **🔎 ניתוח חברה:** ticker input + נתח · company card (+EN-original expander) · 6 KPI · 📈 performance (period cards + selector 1W..MAX+custom + comparison bars + 4 metric cards) · 4 charts (price+MA / volume / RSI / MACD) · financials & valuation tables · 7 score bars · technical section · 3 scenario cards + confidence meter · pros/cons · competitive/regulation · final opinion · HTML download.
- **💎 הזדמנויות:** 5 KPI · Score V2 info card · filter form · counter · table/cards toggle · data grid (sort/select→analyze/CSV) + search · opp cards · sector treemap · sector table.
- **🗺️ סקטורים:** strong/weak cards · score bar chart · ranked table.
- **🚨 התראות:** severity-grouped alert cards.
- **📊 אינטליגנציית שוק:** 4 health metrics · scored table · backtest table.
- **⚙️ הגדרות:** data status · refresh · about.

## Stock data fields
Ticker · Name · Sector(EN+HE) · Industry · Price · DailyChange% · Score · **ScoreV2** ·
Fundamental/Quality · Sector · News · Risk(score+level) · **Trust** · Valuation ·
ExpectedUpside% · Confidence · returns 1W/1M/3M/6M/YTD/1Y/3Y · 52w hi/lo · DistFromHigh% ·
Beta · Volatility · MaxDrawdown · RSI14 · MA20/50/100/200 · MACD · ATR · support/resistance ·
VolRatio · tags(opportunity type) · HistWinRate · MarketCap · fundamentals
(RevGrowth/EPSGrowth/FCFGrowth/OpMargin/D-E/ROIC/PEG/FwdPE/ROE/margins/FCF/debt/cash/EPS) ·
analyst targets (high/mean/low).

## Filters (💎 only)
סקטור (selectbox) · רמת סיכון (multiselect) · סוג הזדמנות (multiselect) · ציון מינ׳ Score V2
(selectbox thresholds) · מומנטום מינ׳ 3ח׳ (selectbox) · תמחור מינ׳ (selectbox) · search (text).
Apply via `st.form` (החל/איפוס). Deep-dive: period selector (1W..MAX) filters the perf window.

## Responsive audit → see the table in chat. Headlines:
**Missing on mobile entirely:** 🔎 Company Analysis (whole screen), 📊 Market Intelligence,
⚙️ Settings, the opportunity filters, click-through-to-analysis, full KPI strips, treemap,
ranked/backtest tables.
**Needs adaptation:** all `st.dataframe` → cards; filter form → accordion (field-per-row);
horizontal radios → scroll pills; the 4 deep-dive charts → low/stacked.
**OK as-is:** alerts cards, sector cards, RTL.

## Work plan (Route A) + complexity
1. Mobile Company Analysis screen — 🔴 high priority, **high** complexity.
2. Click-through (analyze button → mobile analysis) — 🔴 high, medium.
3. Mobile filter accordion — 🟠 medium, medium.
4. Mobile KPI strips (home + opportunities) — 🟠 medium, low.
5. Mobile Market Intelligence — 🟡 low, medium.
6. Mobile Settings (refresh + about) — 🟡 low, low.
7. Mobile home polish (gauge + S&P sparkline) — 🟡 low, low.
8. Overflow/RTL/touch QA — 🟠 medium, low.

Implementation note: mobile click-through requires switching mobile nav from `st.tabs`
(can't switch programmatically) to a **session-state-driven page** + pills, so an
"analyze" button can set the target page.
