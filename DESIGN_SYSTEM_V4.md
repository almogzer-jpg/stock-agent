# Stock Agent Pro — Design System V4 (Phase 2, for approval)

Status: **proposal awaiting approval**. Nothing in the running app follows this yet.
Companion documents: `UX_UI_AUDIT_V4.md` (why), `PRODUCT_IDENTITY.md` (rules).
Visual prototypes: the "Stock Agent V4 — Design Direction" canvas,
https://claude.ai/artifact/QedrmWWUvZH6agpjdaXrDP (private), five screens, each in light and
dark, plus the design-system sheet. Source copies: `docs/v4/prototypes/`. All numbers in the
prototypes are real system data (closes of 28/10/2026, analyst consensus of 29/10/2026).

---

## 1. Identity

**One sentence.** A calm research desk: the conclusion first, the evidence one step away.

**Character.** Quiet surfaces, one accent, strong type, numbers that line up, colour only
when it means something. Light is the default and the reference. Dark is designed for
long evening sessions, not inverted.

**What we stop doing.** Emoji as icons, gradients, coloured left borders on cards, five
accents on one screen, cards around every number, flow language for estimates.

**Principles**
1. Answer first. Every screen opens with its conclusion in plain Hebrew.
2. One verdict everywhere (`verdict.py`). Presentation depth changes, the call never does.
3. Progressive disclosure. Simple depth shows the decision and three reasons. Professional
   depth expands the same page, it does not send you elsewhere.
4. Numbers are first-class: tabular, aligned, signed, with units and a date.
5. Honest uncertainty: reliability next to every verdict, "דורש אימות" on suspicious data.

---

## 2. Colour tokens

Contrast measured against WCAG 2.2 (ratio vs. the three surfaces). Every text token passes AA
(4.5:1) on every surface in both themes.

### Light (default)

| Token | Hex | Use | Contrast bg / surface / surface-2 |
|---|---|---|---|
| `bg` | #F6F5F2 | warm off-white canvas | — |
| `surface` | #FFFFFF | cards, tables, sidebar | — |
| `surface-2` | #F1EFEA | table header, hover, inputs | — |
| `border` | #E6E3DC | hairlines | — |
| `border-strong` | #D6D2C8 | inputs, focus-adjacent | — |
| `text` | #111827 | primary text | 16.3 / 17.7 / 15.4 |
| `text-2` | #475467 | secondary text | 7.1 / 7.7 / 6.7 |
| `text-3` | #5F6B7C | captions, meta | 5.0 / 5.4 / 4.7 |
| `accent` | #2547C9 | links, primary actions, active nav | 6.8 / 7.4 / 6.5 |
| `accent-soft` | #EDF1FD | active nav background | — |
| `positive` | #0B7A4B | gains, "שווה לשקול קנייה" | 4.9 / 5.4 / 4.7 |
| `warning` | #94580A | "להמתין", caution | 5.3 / 5.7 / 5.0 |
| `negative` | #B42318 | losses, "לא עכשיו" | 6.0 / 6.6 / 5.7 |
| `*-soft` | #E8F4EE · #FBF1E2 · #FCEDEB | badge backgrounds | 4.8 · 5.1 · 5.8 |

### Dark

| Token | Hex | Contrast bg / surface / surface-2 |
|---|---|---|
| `bg` | #0E1218 | — |
| `surface` | #151B23 | — |
| `surface-2` | #1C2430 | — |
| `border` | #273141 | — |
| `text` | #E8ECF2 | 15.8 / 14.6 / 13.2 |
| `text-2` | #AAB4C2 | 9.0 / 8.3 / 7.5 |
| `text-3` | #8E99AA | 6.5 / 6.0 / 5.4 |
| `accent` | #8FA9FF | 8.3 / 7.7 / 6.9 |
| `positive` | #55C795 | 8.9 / 8.2 / 7.4 |
| `warning` | #E2B14E | 9.5 / 8.8 / 7.9 |
| `negative` | #F38B81 | 7.9 / 7.3 / 6.6 |
| `*-soft` | #13291F · #2A2314 · #2D1B1B · accent #1D2847 | 7.3 · 7.9 · 6.9 · 6.4 |

Dark is not an inversion: surfaces step up in lightness instead of using shadows, accents
are desaturated so green and red do not glow, and secondary text is lighter than a simple
inversion would give, to stay comfortable on long reads.

**Colour rules.** Colour never carries meaning alone: every verdict and change pairs colour
with an icon shape and a word or a sign (+/−). Red and green are reserved for direction and
verdicts. Charts use the accent for price and dotted lines for levels.

---

## 3. Typography

**Family: Heebo** (Google Fonts, variable 300–800), for Hebrew and Latin.
Evaluation done on the actual font files (fontTools, 29/10/2026):

| Candidate | Digits | Notes | Decision |
|---|---|---|---|
| **Heebo** | all digits share one width by default (tabular) | neutral, modern, excellent Hebrew, Roboto-based Latin | **chosen** |
| Assistant | proportional, no tabular feature | elegant but numbers will not align in tables | rejected |
| Rubik | proportional, tabular via `tnum` | rounded, friendly, reads less "financial" | rejected |

Numbers still get `font-variant-numeric: tabular-nums` so a future font swap keeps alignment.

| Role | Size / line height | Weight | Notes |
|---|---|---|---|
| Page title | 28 / 36 | 700 | one per page |
| Section heading | 20 / 28 | 650 | |
| Card heading | 16 / 24 | 600 | |
| Body | 15 / 24 | 400 | 16 / 26 on phones |
| Secondary | 13.5 / 20 | 400 | `text-2` |
| Caption / meta | 12.5 / 18 | 500 | `text-3`, minimum size anywhere |
| Table | 14 / 20 | 400, figures 500 | tabular |
| Key number | 28 / 32 | 700 | prices in headers |
| Verdict | 22 / 28 | 700 | decision block |

No text below 12.5 px. Weights limited to 400, 500, 600, 700. Hierarchy comes from size and
weight first, colour last.

**Bidi rules.** Tickers, prices, percentages and English names are wrapped in an isolated
LTR span (`<bdi>` or `unicode-bidi: isolate`). Percent sign after the number, sign before
it: `+3.7%`. Currency before: `$1,373.72`. Dates `DD/MM/YYYY`. Arrows in Hebrew lines use
"←" for "from → to".

---

## 4. Space, shape, depth

- Spacing scale (px): 4, 8, 12, 16, 20, 24, 32, 40, 56. Card padding 20 (16 on phones),
  section gap 32, table cell 12 × 16.
- Radius: 6 inputs and badges, 10 cards and tables, 14 the decision block, full for pills.
- Shadow (light only): `sm` 0 1px 2px rgba(17,24,39,.05), `md` 0 6px 20px rgba(17,24,39,.07)
  for menus and dialogs. Dark uses surface steps, no shadows.
- Borders: 1 px `border`. No thick or coloured side borders.

---

## 5. Layout and breakpoints

| Width | Layout |
|---|---|
| ≥ 1280 | sidebar 248 px + content max 1180 px, 12-column grid, 24 px gutters |
| 1024–1279 | collapsible sidebar (icons, 64 px) + content |
| 768–1023 (tablet) | sidebar as drawer, two-column grids become one where needed |
| < 768 (phone, tested at 320/375/390/430) | top bar + bottom navigation, single column, 16 px gutters |

Company page desktop: main column 8/12 (decision, levels, chart, sections) and a 4/12
side column (key facts, events, sources). Phone: one column in the same order.

---

## 6. Information architecture

Seven destinations, each with its own URL (`st.navigation`):

| New destination | Contains (from today's pages) |
|---|---|
| **היום** Today | morning brief, global markets strip, today's opportunities, what changed, sector trends, events |
| **הזדמנויות** Opportunities | scanner table, filters, discovery lists (undervalued, momentum, quality) |
| **ניתוח חברה** Company | the flagship company page, reached from any row or from search |
| **שווקים** Markets | indices, global assets, sectors, macro, crypto (merges Sectors + global part of Market Intelligence) |
| **התראות** Alerts | grouped alerts, one row each, with direct analysis link |
| **רשימת מעקב** Watchlist | saved companies, what changed since saving, holder guidance |
| **הגדרות** Settings | theme, view depth, methodology, data reliability, research results, glossary |

Removed as separate places: the glossary page (terms explained in place), the separate
simple-mode page set (depth becomes a toggle on the same pages), "Market Intelligence" as a
mixed page (split into Markets and Settings › Methodology). Diagnostics stays at `?diag=1`.
No portfolio holdings module. The optional "I own this stock" switch on a watchlist item only
changes which guidance line is shown, no quantities or prices are entered.

**Desktop navigation.** Left-hand (RTL: right-hand) sidebar, collapsible: brand, global
company search (Hebrew/English name or ticker), grouped items (ראשי: היום, הזדמנויות, ניתוח
חברה · שווקים: שווקים, התראות · שלי: רשימת מעקב), settings and theme at the bottom. Line icons,
one stroke weight, no emoji. Active item: `accent-soft` background, accent text, no side bar.

**Phone navigation.** Top bar: brand, search button, depth toggle. Bottom bar with five items
at 56 px height, labels 12.5 px: היום · הזדמנויות · חיפוש · מעקב · עוד. "עוד" opens a sheet
with שווקים, התראות (with count), הגדרות. The bar sits above the Streamlit Cloud badge when
framed.

**Depth toggle.** "פשוט / מקצועי" segmented control in the top bar, remembered per browser.
Simple depth: decision, three reasons, risks, levels, one chart. Professional depth: the same
page with all sections expanded, score breakdown, statements, indicators, sources.

---

## 7. Components

| Component | Spec |
|---|---|
| **Verdict badge** | pill, 6 px radius, soft background + strong text + icon (check / clock / stop / dash) + label. Four states only: לשקול קנייה, להמתין, לא עכשיו, אין מספיק מידע |
| **Decision block** | surface card, 14 px radius, verdict 22 px, one-sentence why, three reasons, two risks, holder line, reliability chip. The only "hero" element on a page |
| **Data table** | white surface, 10 px radius, sticky `surface-2` header, 52 px rows, right-aligned text, tabular numbers, sortable headers with `aria-sort`, hover row tint, the whole row is the link (keyboard: Enter), loading skeleton rows, empty state sentence. Phone: becomes a list of rows with two lines (name + verdict, price + change) and an expand chevron |
| **Stat** | label 12.5 `text-3`, value 22–28 tabular, delta with sign and colour, optional date |
| **Card** | used for summaries and decisions only. 1 px border, no shadow in dark, 20 px padding |
| **Level bar** | horizontal track with support, price, target and resistance markers, labels placed above/below alternately so they never overlap |
| **Price chart** | Plotly, theme-aware, accent line, dotted level lines with right-edge labels, period control 1W 1M 3M 6M YTD 1Y 3Y 5Y MAX (phone: 1M 3M 6M 1Y 5Y + "עוד") |
| **Term** | dotted underline, tooltip on hover and focus, `aria-describedby` so screen readers read it, max 2 sentences |
| **Buttons** | primary (accent fill), secondary (border), quiet (text). 40 px desktop, 44 px phone |
| **Inputs** | 40 px, `surface-2` fill, visible label (can be visually hidden), search has a submit button |
| **Segmented control** | for periods, filters and depth. Selected: surface + `sm` shadow (light) or surface-2 (dark) |
| **Alert row** | icon, severity word, one sentence, time, ticker link. No card per alert |
| **States** | skeleton (shimmer disabled under reduced motion), empty (one sentence + next action), error (what happened + retry), stale data banner with date |

---

## 8. Accessibility standard (WCAG 2.2 AA)

- Contrast verified for every token pair (section 2). Focus ring: 2 px accent outline,
  2 px offset, on every interactive element.
- Every control is a real `button`, `a`, `input` or `select` with a label. Navigation
  options are announced by name, not index.
- Touch targets ≥ 44 × 44 px on phones. No hover-only information.
- Colour is never the only signal (icons + words + signs).
- `prefers-reduced-motion`: no fades, no shimmer.
- Zoom to 200% without horizontal scrolling of the page (tables scroll inside their box).
- Charts get a text summary ("עלתה 60% בשנה, במגמת עלייה, מעל התמיכה $1,131").

---

## 9. Implementation in Streamlit (Option A, recommended in the audit)

- `.streamlit/config.toml`: `[theme.light]` and `[theme.dark]` with the tokens above,
  `[[theme.fontFaces]]` for Heebo, `headingFont`, `baseRadius`, `borderColor`. Streamlit's
  own light/dark/system switch persists the choice per browser.
- One module `dashboard/ds.py`: tokens for both themes, CSS emitted once per run keyed by
  `st.context.theme.type`, and component functions (verdict badge, stat, table, card,
  alert row, level bar, term). Pages call components, never write inline styles.
- `st.navigation` with grouped `st.Page` entries (real URLs, working back button).
- Tables: a small HTML component with client-side sorting and keyboard support, phone list
  rendering, used everywhere a comparison is shown.
- Plotly template per theme, chosen from `st.context.theme.type`.
- To validate in a short spike before page work: theme switch without flash, chart re-colour
  on switch, table component keyboard behaviour.

---

## 10. Quality gate per page (from the V4 brief)

Each redesigned page is checked on desktop and phone, light and dark, RTL, keyboard,
contrast, data integrity (same verdict as the engine), navigation and load time, and must pass
the 14 questions of the brief before the next page starts.
