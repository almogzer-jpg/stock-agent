# UI COMPONENT INVENTORY — Phase 17

The institutional design system. All tokens live in `dashboard/theme.py`; the
Home screen composes these in `dashboard/app.py`. Legacy color names
(`GREEN/AMBER/RED/BLUE`) are remapped to the new palette so **every existing tab
and the mobile UI inherit the new look automatically**.

## Design tokens

### Color
| Token | Hex | Use |
|---|---|---|
| `BG` | `#08111f` | app background |
| `CARD` | `#102040` | card surface |
| `ELEV` | `#16284d` | elevated surface / gradient top |
| `BORDER` | `#1f3257` | hairline borders |
| `PRIMARY` (=BLUE) | `#00C2FF` | brand / interactive accent |
| `POSITIVE` (=GREEN) | `#00E676` | bullish / good |
| `WARNING` (=AMBER) | `#FFC107` | caution |
| `NEGATIVE` (=RED) | `#FF5252` | bearish / bad |
| `TEXT` | `#E6EDF7` | primary text |
| `MUTED` | `#94A3B8` | secondary text |

### Typography
| Role | Size / weight |
|---|---|
| KPI number | 38px / 800 (mobile 30px) |
| Card title | 16px / 800 |
| Section h2 / h3 | 22 / 18px / 800 |
| Body | 15px / 400 |
| Meta / sub | 12–13px / `MUTED` |

### Spacing & shape
Cards: radius 16px, padding 16–20px, gap 14–16px, gradient `ELEV→CARD`,
shadow `0 6px 20px rgba(0,0,0,.28)`. Single-side accent via `border-right`/`border-top`.

## Components (in `theme.py`)

| Component | Class / helper | Notes |
|---|---|---|
| KPI card | `.kpi` / `.kpi-grid` | icon, 38px number, label, sub, color top-border, status dot, **native tooltip** (`title`), hover-lift |
| Elevated card | `.ic-card` / `.ic-title` / `.ic-sub` | generic premium card with fade-in |
| Score bar | `.sbar` + `score_bar(label,value)` | number + animated fill, color via `score_color()` |
| Action card | `.act` + `action_card_html(idx,h)` | priority accent, why / risk impact / benefit / confidence |
| Opportunity card | `.opp` + `opp_card(rank,r)` | sparkline + 6 score bars + meta + why/risks/events |
| Sparkline | `sparkline_svg(values)` | inline SVG (no Plotly → fast), color by direction |
| Severity badge | `.badge` `.b-crit/.b-high/.b-med/.b-low` | pill, color-coded |
| Regime gauge | `regime_gauge()` (Plotly) / SVG ring (mockup) | angular gauge + threshold marker |
| Top bar | `.topbar` | brand + status pill + date |
| Loading skeleton | `.skeleton` | shimmer placeholder |
| Plotly theme | `style_fig()` | transparent bg, grid `BORDER`, hover label, 350ms transition |

## Color & helper functions

| Function | Purpose |
|---|---|
| `score_color(v)` | green ≥66 · amber ≥40 · red <40 |
| `regime_color(score)` | green ≥60 · amber 40–59 · red <40 |
| `sparkline_svg(values,w,h)` | direction-colored inline SVG sparkline |
| `score_bar(label,value,maxv,color)` | one labeled animated progress bar |

## Micro-interactions

| Interaction | Mechanism | Where |
|---|---|---|
| Fade-in on cards | `@keyframes fadeUp` | all cards |
| Hover lift | `transform: translateY(-3px)` | KPI + opportunity cards |
| Progress-bar fill | `@keyframes grow` (live) / width transition (mockup) | score bars |
| Animated count-up | JS counter | mockups (Streamlit strips inline JS, so the live app uses a fill/fade reveal) |
| Native tooltips | `title` attribute | KPI cards |
| Expand/collapse | `st.expander` + inline drill-down panel | Home opportunities, method notes |
| Loading skeleton | shimmer class | available for slow panels |

> **Live-app note:** Streamlit sanitizes `<script>` inside `st.markdown`, so the
> running dashboard uses **CSS-only** animations (fades, transitions, keyframe
> fills) and native `title` tooltips. The standalone HTML mockups add JS-driven
> count-up and gauge sweep for the full premium feel.
