# UX DECISIONS — Phase 17

Designed for a portfolio manager opening this every morning: **faster decisions,
less cognitive load, fewer clicks.** Not "look impressive" — look *decisive*.

## Guiding principles (and how each was honored)

1. **Every screen answers: what / why / what to do.** Home is now ordered exactly
   that way: KPI strip (what) → regime gauge + factors (why) → action cards (what to do).
2. **Any key metric understood in 2 seconds.** KPI cards use a 38px number, a color
   indicator (top-border + dot), a one-line label, and a sub-explanation — no
   reading required to grasp state.
3. **No walls of text / big tables on the decision screen.** The Home table was
   replaced by opportunity *cards*; dense tables remain only on detail/scanner tabs
   where scanning many rows is the actual job.
4. **Visual hierarchy drives the eye to decisions.** Color encodes meaning
   (green/amber/red = good/caution/bad), accents point to the most urgent action,
   and the highest-priority action card is red and first.
5. **Feels like a premium product.** Gradient card surfaces, consistent radius,
   institutional palette, tasteful motion — without sacrificing the <3s load.

## Key decisions & rationale

| Decision | Why |
|---|---|
| Remap legacy color names to the new palette instead of renaming everywhere | The whole app + mobile re-skins instantly with zero risk to other tabs; honors "theme + Home first, then expand." |
| KPI strip of 6 cards at the very top | A morning glance answers "is anything on fire?" before any scrolling. |
| Regime as an angular gauge + ✓/✗ contributing-factor chips | A gauge reads in <1s; the chips show *why* (S&P trend, VIX, breadth) without a paragraph. Factors are derived from existing artifact data — no logic change. |
| "What should I do today" as P1/P2/P3 cards with why / risk-impact / confidence | Turns the existing decision engine output into a ranked, self-justifying to-do list — the manager's first action surface. |
| Opportunity cards with inline 6 score bars + sparkline | The score breakdown (the system's transparency edge) is visible at a glance; the sparkline gives price context without a chart widget. |
| Inline sparkline as hand-built SVG, not Plotly | One Plotly instance per card would hurt the <3s budget; SVG is instant and dependency-free. |
| Drill-down via inline "🔍 ניתוח" toggle, not a page jump | Keeps the manager in context (fewer clicks); expands full why/risks/catalysts in place. |
| Mobile = dedicated bottom-nav layout, not a shrunk desktop | Thumb-reachable navigation, card-only, no horizontal scroll, sticky market summary. |
| CSS-only animation in the live app | Streamlit strips inline JS; CSS keyframes/transitions deliver motion safely. Mockups show the full JS version. |

## Performance decisions

- **No new network calls** — Home reads the same precomputed artifacts
  (`market_overview.json`, `results.csv`, `portfolio.json`, `alerts_center.json`,
  `system_health.json`). Verified: dashboard boots in ~1s, Home renders with no
  exceptions.
- **SVG sparklines + CSS animation** instead of many Plotly figures keeps
  interactions snappy.
- Only **2 Plotly charts** on Home (regime gauge + S&P trend).

## Before / After

> Pixel before/after screenshots could not be captured (browser-automation tooling
> in this environment times out / freezes — a tooling limitation, not an app issue).
> The standalone mockups (`desktop_home.html`, `mobile_home.html`) and the inline
> renders are the visual "after"; the table below is the structural diff.

| Aspect | Before | After |
|---|---|---|
| Palette | navy `#0e1726`, mixed pastel status colors | institutional `#08111f` + crisp `#00C2FF/00E676/FFC107/FF5252` |
| Home opening | text insight card + 3-column overview | 6-KPI executive strip (38px numbers) |
| "What is the market?" | regime number inside a text card | angular gauge + ✓/✗ factor chips |
| "What do I do?" | buried in a separate Decisions tab | P1/P2/P3 action cards on Home |
| Opportunities | text cards, no score viz | cards with sparkline + 6 animated score bars + Analyze/Add |
| Typography | ~1.6rem metrics, 13px body | 38px KPIs, clear 15px body, more spacing |
| Motion | none | fade-in, hover-lift, animated fills, tooltips |
| Mobile | functional cards | bottom-nav app shell, sticky summary |

## What was implemented now vs. next (per your "theme + Home, then expand")

- **Done & live-verified:** global institutional theme (all tabs + mobile inherit
  it), fully redesigned executive **Home**, drill-down, mockups (desktop + mobile),
  this design package.
- **Next (tab-by-tab):** Sectors heatmap/treemap, Portfolio institutional page
  (allocation donut, risk-contribution, correlation heatmap), Alert Center cards,
  enhanced tables (sticky headers, sorting, conditional colors, expandable rows),
  and applying card-first layouts to Scanner & Detail.
