# Stock Agent Pro — Design System (v1)
**The single source of truth. Every page must follow it. No page invents its own styling.**
Canonical implementation: `dashboard/theme.py` (tokens + CSS classes) + `.streamlit/config.toml` (native widgets).
Creative direction: calm · expensive · intentional · data-first. If a screen looks "good enough" — it isn't done.

---

## 1. Typography
- **Family:** Inter (Google Fonts, weights 400/500/600/700) → fallback IBM Plex Sans → Segoe UI.
- **Scale (fixed — no other sizes):**

| Role | Size | Weight | Notes |
|---|---|---|---|
| Page title (`###`/h2-h3) | 30px | 700 | letter-spacing −.3px |
| Section title (`####`/h4) | 23px | 600 | margin-top 2.2rem — sections breathe |
| Card title (`.ic-title`) | 20px | 600 | |
| Primary number (`FS_KPI`) | 40px | 700 | letter-spacing −1.2px; ONE per card max |
| Secondary number (`FS_NUM2`) | 28px | 600 | |
| Normal value | 18px | 600 | header metrics |
| Body / descriptions (`FS_BODY`) | 16px | 400 | line-height 1.7 |
| Footnote / captions (`FS_FOOT`) | 14px | 400 | `st.caption` |
- **Rules:** max weight 700 and only on numbers/page-titles; everything else ≤600. Never center Hebrew paragraphs — always right-aligned RTL. Short sentences; bullets over blocks.

## 2. Color
| Token | Hex | Use — and ONLY this use |
|---|---|---|
| `BG` | `#0B0F17` | app canvas |
| `CARD` | `#131926` | every surface |
| `ELEV` | `#1A2233` | hover / raised / active-nav |
| `BORDER` | `#232D40` | hairlines (tables, dividers) — never around cards |
| `TEXT` | `#F4F6F8` | primary text |
| `SECONDARY` | `#C8D2E0` | supporting text |
| `MUTED` | `#94A3B8` | labels/footnotes — **contrast floor, nothing darker** |
| `POSITIVE` | `#34D399` | gains/good ONLY |
| `NEGATIVE` | `#F87171` | losses/bad ONLY |
| `WARNING` | `#FBBF24` | caution ONLY |
| `PRIMARY` | `#5EA8FF` | actions/links/interactive ONLY |
| high-risk orange | `#fb923c` | the single extra step between warn↔negative (risk ladders) |
- **Rules:** color = meaning, never decoration. A screen may not introduce hues outside this table. Score coloring only via `score_color()` (≥66 green · ≥40 yellow · else red); regime via `regime_color()`.

## 3. Spacing
- Base unit 4px. Card padding **24–26px** (28–30 for hero cards). Grid gap **16px**. Card margin-bottom **20px**. Section separation = h4 margin-top 2.2rem (+ `st.divider` only between major zones). `block-container` max-width 1460px.
- Nothing compressed: if a card needs to shrink padding to fit — split the card.

## 4. Component Library (classes in theme.py — reuse, never re-invent)
| Component | Class / helper | Contract |
|---|---|---|
| Surface card | `.card` / `.ic-card` (+`.ic-title`,`.ic-sub`) | borderless, flat, radius 16 |
| KPI card | `.kpi` in `.kpi-grid` (+ `kpi_html()`) | small label → ONE big number → short sub; accent via `--ac`; native `title` tooltip |
| Score bar | `score_bar(label,value)` | number + semantic fill |
| Badge/pill | `.tbadge`/`.badge`/`.secbadge` | 13.5px/600, ELEV bg, text = semantic color; recommendations & statuses are ALWAYS pills, never bare colored text |
| Institutional table | `.sectbl` (+`.miniprog`) | THE table for comparisons — see §7 |
| Data grid | `st.dataframe` | only when built-in sort/row-select/CSV is required (💎) |
| Ranking item | `.rcard`/`.pitem` | compact lists |
| Rich stock card | `.ocard` (+`.oc-*`) | avatar-initials, ticker XL, name UNDER it, badges, metric rows w/ `.info` tooltip |
| Action card | `.act` | priority accent bar |
| Scenario card | `.scen` | soft tinted bg, right accent |
| Perf chips | `.chiprow`/`.chip` (`.cl` label, `.cv` value) | any horizontal metric strip |
| Confidence meter | `.confmeter`/`.conftrack`/`.conffill` | |
| Buttons | quiet default (transparent, border, hover→blue); `type="primary"` = filled blue, ONE per view | min-height 40px desktop / 48px mobile |
| Filters | inside `st.form` card; labeled selectboxes w/ threshold names ("70+ חזק"), risk = multiselect, apply=primary + reset; never free sliders | |
| Empty state | one-line `st.info`/caption: what's missing + how to fix ("הרץ scanner.py") — never blank | |
| Loading | `.skeleton` shimmer for known layouts; spinner only for live fetches, WITH text ("מנתח את NVDA…") | |
| Tooltips | native `title=` on KPI/chips; `.info` "?" circles on metric rows; `help=` on inputs — every non-obvious metric MUST have one | |
| Modals | none — use expanders/pages (Streamlit dialogs break flow) | |

## 5. Motion
- Durations: hover 150ms · fills/reveals 250–600ms `cubic-bezier(.2,.8,.2,1)` · fadeUp entrance .35s.
- Allowed: fadeUp on cards, background-tint hover, bar `grow`, skeleton shimmer, chart transition 250ms. **Forbidden:** pulses, glows, parallax, anything that moves without user cause.

## 6. Charts (`style_fig()` is mandatory)
- Bg = `BG`; font Inter 13 `TEXT`; ticks `SECONDARY` 12; grid `BORDER`; legend TEXT on rgba(19,25,38,.85) + border; hover label CARD/TEXT.
- Line colors fixed: Price `#5EA8FF` · MA20 `#FBBF24` · MA50 `#B388FF` · MA200 `#F1F5F9` · up `#34D399` · down `#F87171` · volume `#26A69A` (all ≥3:1 — tested).
- Support line green dotted + Hebrew label; resistance red dotted. Date axes ALWAYS: `%d/%m/%y`, hover `%d/%m/%Y`, weekend rangebreaks. Heights: hero 320 · standard 260–300 · mobile 200–280. Heavy/secondary charts (RSI/MACD/volume) live behind expander + toggle (lazy).

## 7. Tables
- Comparison of entities → `.sectbl`: right-aligned headers `MUTED` 12.5px/600, row padding 10–12px, row hover `ELEV`, hairline row borders only.
- Cell grammar: entity = bold ticker + small name underneath; score = `.miniprog` + colored number; status = pill; % = signed & colored.
- Row count ≤ 12 on overview pages; more → dedicated grid page. Every row must have a click-path to analysis (row-select or `🔎 TICKER` button strip).
- Mobile: tables become cards — never horizontal scroll.

## 8. Mobile (separate experience — `dashboard/mobile.py`)
- Sticky bottom nav (`.st-key-mnav`, fixed, safe-area padding); pages = one question each.
- Type: body 16 · titles 20 · key metrics 28–32. Touch ≥48px. KPI grid 2-up.
- Horizontal chips for metric strips; accordions for depth (analysis: decision card open, rest collapsed); charts behind toggle; company name always under ticker; zero horizontal overflow.

## 9. Accessibility
- WCAG AA enforced by tests (`tests/test_accessibility.py`): text ≥4.5:1, graphics ≥3:1 on `BG`; `MUTED` is the darkest text allowed.
- Color-blind safety: color never alone — always paired with sign (+/−), emoji-shape (🟢🟡🔴), or label.
- Focus/keyboard: native Streamlit widgets for all interactions (keyboard-reachable); custom HTML is display-only.
- RTL everywhere; LTR only inside price-zone bars/charts where numeric direction matters.

## 10. Voice & content
- Hebrew, concise, professional. Every metric answers "למה זה חשוב" via tooltip or sub-line.
- Mandatory labeling: עובדה / מחושב / תצפית היסטורית / תרחיש / הערכת מודל. Missing data = "אין נתון זמין" — never invented, never blank.
- No AI-voice ("המערכת חושבת") — data-voice ("הנתונים מצביעים"). Disclaimer on every surface: מידע בלבד, לא ייעוץ השקעות.

## 11. Page template (every screen follows)
1. **Answer first** — one line/card that answers the page's question.
2. **Evidence** — 1-2 premium components (table/chart/cards), largest = most important.
3. **Action** — explicit path onward (🔎 analyze / navigate).
4. **Footnote** — method + disclaimer.
Per-page gate before "done": 11-criteria score ≥9.5 (incl. First Impression) + benchmark vs Bloomberg/Koyfin/TradingView/Finviz/SeekingAlpha.
