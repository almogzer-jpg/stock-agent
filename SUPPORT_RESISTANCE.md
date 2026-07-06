# SUPPORT_RESISTANCE.md — Support & Resistance Methodology (Phase 24)

> **הרמות הן הערכות טכניות בלבד, מנתוני מחיר אמיתיים — לא רצפה או תקרה מובטחת,
> ולא ייעוץ השקעות.**

## Engine
`technicals.sr_levels(df)` — pure function over real OHLCV history. Returns `None`
when there isn't enough history (never invents levels).

## Methodology

### 1. Swing pivots (primary)
- Lookback: last ~130 trading days (~6 months), pivot window ±5 sessions.
- A **pivot high** is a day whose High is the max of its ±5-day window; a
  **pivot low** is the min of its window (`technicals._pivots`).
- **Volume confirmation:** a pivot whose volume was above its 20-day average is
  flagged; volume-confirmed levels are **preferred** when picking the nearest level.

### 2. 52-week extremes
The 52-week high/low join the candidate pool (resistance/support respectively).

### 3. Moving averages (dynamic levels)
MA20 / MA50 / MA100 / MA200 within **2% of the current price** are reported as
**dynamic support/resistance** (labels only — they don't override the static level).

### Level selection rules
- **Support** = nearest candidate **below** price (max of those below).
- **Resistance** = nearest candidate **above** price (min of those above).
- A candidate must clear the price by **≥0.1%** — otherwise rounding could turn
  the current bar itself (e.g. today being the 52w high) into a fake level.
- No candidate → the field is `None` and the UI shows **"אין רמת תמיכה/התנגדות אמינה"**.

### Distances
`dist_support_pct = (support/price − 1)·100` (negative) ·
`dist_resistance_pct = (resistance/price − 1)·100` (positive).

### Breakout / Breakdown
- `breakout_level` = the resistance; `breakdown_level` = the support.
- Price above **every** observed level → status **breakout** → "פריצה מעל התנגדות".
- Price below every observed level → status **breakdown** → "שבירה מתחת לתמיכה".

### Risk / Reward
`RR = dist_resistance_pct / |dist_support_pct|` —
**> 2.0 אטרקטיבי · 1.0–2.0 מאוזן · < 1.0 לא אטרקטיבי.**
Computed only when both levels exist.

### Interpretation (deterministic Hebrew sentence)
Closer to resistance → "יחס סיכון/סיכוי פחות אטרקטיבי"; closer to support → "נוח יותר";
breakout/breakdown get their explicit sentence.

## Where it appears
- **🔎 ניתוח חברה (desktop):** dedicated levels panel (price, support, resistance,
  breakout/breakdown levels, R/R + label, dynamic MAs, interpretation) + green/red
  chart lines labeled "תמיכה $X" / "התנגדות $Y" on the price chart (with MA20/50/200).
- **Mobile analysis:** compact cards (תמיכה / התנגדות / יחס סיכון-סיכוי / סטטוס).
- **💎 Opportunities table:** compact columns — תמיכה `$210.40 (-5.5%)`,
  התנגדות `$235.80 (+5.9%)`, סיכון/סיכוי.
- **Artifacts:** `run.py` (watchlist → results.csv) and `scanner.py` (universe.json)
  store Support / Resistance / DistSupport% / DistResistance% / RiskReward per ticker.

## Quality gates (tests/test_technicals.py)
- Support strictly below price; resistance strictly above (margin-guarded).
- Distance math verified against the definition.
- R/R math + classification bands verified.
- Breakout status when price exceeds all observed levels.
- Short history → `None` (no fake levels).
