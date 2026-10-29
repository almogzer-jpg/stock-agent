# Stock Agent Pro — UX/UI Audit V4 (Phase 1)

Date: 29/10/2026 · Branch: `claude/beginner-review` · Auditor: Claude (Opus 5.5)

## 0. Scope and method

**What was inspected.** The running application, not only the code:

- The live production site at the start of the session (`docs/v4/audit/production-29-10-2026/`).
- The current branch running locally, captured with a reproducible headless-Chrome script
  (`docs/v4/capture.py`): 9 professional desktop screens, 5 professional phone screens,
  6 simple desktop screens, 5 simple phone screens. Desktop viewport 1280 px wide,
  phone 375 px wide at 2x. All files are in `docs/v4/audit/`.
- Interactions actually exercised in a browser during this session: sidebar navigation,
  phone bottom navigation, the company search (Hebrew name, English name, ticker),
  "save to my stocks" plus a full reload, the simple/pro mode switch in both directions,
  the professional deep dive, and the floating-badge workaround inside a simulated
  Streamlit Cloud wrapper.

**What was NOT tested** (no claim is made about these): screen-reader output, keyboard-only
navigation end to end, 200% browser zoom, reduced-motion preference, 320/390/430 px widths,
tablet widths, and real phones. These are listed as open items in section 9.

**Two layers exist today.** This branch already contains the unified decision engine and
the simple view built in the previous phase (`verdict.py`, `stockdata.py`,
`dashboard/simple.py`). The production site still runs the older version. Findings below
say which layer they apply to.

---

## 1. Executive summary

1. **The analysis is strong, the presentation is not.** The engines are rich and
   transparent, but every screen shows too much at once, in a dark theme with many
   accent colours, emoji used as icons, and three different card styles.
2. **Contradictory recommendations were the most serious problem** and their root cause was
   architectural (five independent recommendation paths). It is fixed on this branch
   (section 2). It is still visible in production until the branch is deployed.
3. **Navigation is state-based, not URL-based.** Pages have no addresses, the browser
   back button does not move between pages, and deep links are impossible.
4. **Tables are the weakest component.** The opportunities grid is a canvas widget that
   truncates names, hides columns behind horizontal scroll, and is invisible to assistive
   technology. Custom HTML tables cannot sort. The sector table now overflows at 1280 px.
5. **Phone experience is two separate products** (professional phone view and simple view)
   with different navigation, different cards and different density.
6. **Typography has no system.** Sizes from 10.5 px to 40 px appear on one screen. Bidi
   errors corrupt English names and percentages inside Hebrew text.
7. **Streamlit 1.58 can deliver most of the V4 vision** (native light and dark themes,
   custom fonts, URL-based multipage navigation). It cannot deliver a fully custom data
   grid or app-like transitions without custom components. See section 8.

---

## 2. Contradictory recommendations — root cause (documented, fixed on this branch)

| Path that produced a call | Basis | Example of the conflict seen in production |
|---|---|---|
| `classify()` status pill (home, phone cards) | Technical score only | LLY "🟢 מגמה חזקה" |
| Home "highest conviction" table | Sorted by Score V2, ignored timing | LLY ranked #1 |
| `delta.action_for()` | Different thresholds on V2 change | AVGO "להימנע" while its V2 rose |
| `deepdive.recommendation()` | Score scale 78/68/55/45/35 | AAPL "Watch" (cloud) vs "Buy" (local) |
| `investment_decision()` entry quality | RSI and distance to levels | LLY "מתוח — התרחק מרמות אלו" |

A beginner saw LLY as the top opportunity on the home page and "stay away" one click later.
**Fix (previous phase, user-approved):** one engine, `verdict.py`, consumed through one
canonical row per ticker, `stockdata.py`. The timing rules that caused the conflict were
tested on 66,625 historical samples (`research/timing_study.py`) and none improved
3-month excess returns, so none gates the verdict any more. The investment scoring
(Score V2 weights and formulas) was not changed.

Additional data-integrity defects found and fixed in the same phase: company data missing on
Streamlit Cloud for every stock (Yahoo blocks the cloud host, fixed with a dated fallback),
a fundamentals cache that pinned failed pulls for a week, a "computed target" that was a
heuristic presented as a price target, uncalibrated scenario probabilities (37/40/23%),
"Unknown Company" on the phone home, and a per-visitor watchlist that was shared by all
visitors and wiped on every deploy.

**Found in this audit and already fixed on the branch** (bugs, not redesign): the professional
phone deep dive coloured the verdict pill yellow while its dot was green
(`pro-phone-02-analysis.png`), the executive summary still used the old "entry quality"
phrase, and the sector table overflowed at 1280 px after the previous change.

### 2.1 Data-integrity findings from this audit
- `data/global_markets.json` (indices, crypto, gold, oil, rates, USD/ILS) was never committed:
  the `.gitignore` whitelist did not include it, so the production site never had the global
  markets strip. Fixed on the branch (whitelisted). Takes effect after the next daily run.
- The US 10-year yield is stored as 0.5, a scale error (the real value is in the 4–5% range).
  Shown as "דורש אימות" in the prototypes. To fix in `globalmkt.py` during implementation.
- USD/ILS, EUR/ILS and GBP/ILS show daily moves of about +3%, which looks like a stale previous
  close. Requires verification before display.
- VIX appears with two different values from two artifacts (16.91 −3.48% and 17.12 +1.24%).
  One source of truth is needed.

### 2.2 Model findings (research, for the owner's decision)
The technical score (25% of Score V2) showed no link to 3-month excess returns, but higher
scores came with shallower drawdowns. The breakout signal underperformed the rest of the
sample by about 2.6 points. Details in `research/README.md`. No weights were changed.

---

## 3. Cross-cutting findings

### 3.1 Visual identity
- Dark navy canvas with five saturated accents (green, red, amber, blue, orange) used
  decoratively, not only for meaning. On the sector treemap every tile is green, including
  sectors the table next to it says to underweight (`pro-desktop-05-sectors.png`).
- Emoji act as icons in navigation, KPI cards, headings and buttons (🏠 🔎 💎 🗺️ 🚨 📊 ⚙️
  🧭 😶‍🌫️). They render differently per platform and read as informal.
- Three card styles coexist (`ic-card`, `mcard`, `s-card`), plus `kpi`, `chip`, `tbadge`
  and `scen` variants. Radius ranges from 10 to 18 px.
- The header strip on every professional page ("Stock Agent Pro v3.0 · המערכת מעודכנת")
  repeats information that the sidebar already shows.

### 3.2 Typography
- No type scale in use. One deep-dive screen mixes 10.5, 11.5, 12.5, 13, 13.5, 14, 15, 16,
  17, 18, 19, 20, 22, 24, 26, 28, 30 and 40 px.
- The system font stack (Segoe UI on Windows) has weak Hebrew. Headings and body use the same
  family and weights, so hierarchy relies on colour.
- Numbers are proportional, so prices and percentages do not align in tables.
- Bidi corruption: English names lose their final period to the wrong side
  (".Broadcom Inc", ".Apple Inc"), parenthesised percentages flip ("(+47.7% בשנה)" breaks
  across lines), and analyst arrows point the wrong way in Hebrew lines
  ("Outperform → Peer Perform").
- Mixed languages in titles: "Company Deep Dive — ניתוח חברה", "Score V2", "reit".

### 3.3 Information density and hierarchy
- The professional home stacks 12 sections with 4 KPI rows that partly repeat each other
  (market regime appears in the brief, the regime card, the header strip and the sidebar).
- The professional deep dive shows about 60 numbers before the first scroll stops, across
  3 equal-weight columns. The decision, the single most important element, gets one third
  of the width and wraps its own headline (`pro-desktop-02-company-analysis.png`).
- Four different confidence-like numbers sat next to each other in production
  (79%, 67, 84, 92). This branch reduced them to one data-reliability figure plus a clearly
  named signal-agreement figure, but the pro page still shows both close together.

### 3.4 Tables
- Opportunities grid (`st.dataframe`, canvas based): truncated names
  ("Packaging Corporation of Americ"), the rightmost column is cut and needs horizontal
  scroll, column order runs left to right inside a right-to-left page, and the content is not
  exposed to screen readers.
- Custom HTML tables (home, sectors, delta) cannot sort, filter or search, have no sticky
  header, and the 10-column sector table overflows at 1280 px after the latest change
  (the "average risk" column is clipped). Regression to fix in implementation.
- Row actions live in a separate row of buttons under the table, so the click target is far
  from the row it acts on.

### 3.5 Navigation
- Professional desktop: 8 sidebar items with emoji, no grouping, no global search.
- Pages are radio buttons in session state: no URL per page, no working back button, no
  shareable link to a company analysis.
- Phone (professional): 6 bottom tabs. This branch made them fit, but labels are 12 px.
- Phone (simple): 5 bottom tabs, a different set from the professional phone view.
- The floating Streamlit Cloud badge covered the first phone tab in production. It lives in
  the host page and cannot be hidden. This branch lifts the phone nav above it when framed
  (verified in a simulated wrapper).

### 3.6 Copy and terminology
- Jargon without explanation in production: V2, RS, Risk-On, רוטציה דפנסיבית, ציון משטר,
  פירכת התזה, צ'ק-ליסט מוסדי, guidance. The simple view now explains terms with tooltips,
  the professional view does not.
- Inconsistent names for the same thing: "ציון V2", "ציון סופי v2", "Score V2", "ציון איכות".
- Streamlit's English "Press Enter to apply" hint is drawn on top of the Hebrew text in
  search inputs (`simple-desktop-02-check-empty.png` run). There is no visible search button,
  so phone users may not know to press Enter.

### 3.7 Accessibility (observed)
- Sidebar radio options are exposed as "0", "1", "2"… to assistive technology (seen in the
  accessibility tree), not by their labels.
- Colour carries meaning on its own in several places (score bars, sector treemap,
  red/green percentages without a sign on some tiles).
- Tooltips in the simple view are focusable (`tabindex=0`) but their text lives in a
  `data-tip` attribute that screen readers do not announce.
- Positives already in place: AA contrast is unit-tested for the palette, a visible focus
  ring exists, touch targets in the phone views are 48 px or more.

### 3.8 Performance (baseline, measured)
Measured with `docs/v4/capture.py` against the local server (`docs/v4/audit/timings.json`).
"First render" is the time until the main area has content and Streamlit reports idle,
polled every 0.5 s, so values are rounded up and include a 1.5 s settle delay.

| Screen | First render | Until screenshot |
|---|---|---|
| Professional home (desktop / phone) | 2.0 s / 2.0 s | 2.3 s / 2.2 s |
| Professional deep dive, AAPL, cold | — | 11.3 s |
| Professional phone analysis, AAPL | — | 7.3 s |
| Simple Today (desktop / phone) | 2.0 s / 3.6 s | 2.1 s / 3.8 s |
| Simple stock check, live analysis | — | 13.4 s desktop, 15.9 s phone |
| Page switches (any) | — | 4.6–6.2 s including a full rerun |

The live company analysis dominates (Yahoo calls for history, statements, news, plus a
5-year S&P series). Every navigation reruns the whole script. Network on Streamlit Cloud
will be slower than localhost.

---

## 4. Page-by-page findings

### 4.1 Home (professional) — `pro-desktop-01-home.png`, `pro-phone-01-home.png`
- Answers "what changed" well (delta table with cause and verdict).
- Too many parallel blocks: brief, regime card with 4 numbers, capital flow, macro, breadth,
  global strip, delta table, opportunities table, events, analyst actions, attention list,
  research queue, quick actions.
- "לאן זורם הכסף" presents a sector-strength estimate with flow language ("כניסת הון").
  The caption admits it is an estimate, the heading does not. V4 rule: never present
  estimated flows as institutional capital movement.
- "תמונת מאקרו" is an empty card stating that the data is unavailable.
- Analyst targets column is empty until the next daily pipeline run (the field was added on
  this branch).

### 4.2 Company analysis (professional) — `pro-desktop-02-company-analysis.png`
- The decision is correct and consistent now, but visually it is one card among twenty.
- Executive summary sentence 3 still uses the old phrase "איכות הכניסה כרגע" and a semicolon.
- "שולי ביטחון -5.1%" and "אפסייד -4.9%" sit side by side with different definitions.
- The level range bar overlaps its own labels ($332.4 target over $349.3 price).
- Checklist of 14 coloured chips, decision matrix, catalysts, kill-conditions, scenarios,
  statements, valuation, technicals and scores all render expanded. No progressive disclosure.
- Ticker-only search field with an English title.

### 4.3 Watchlist (professional) — `pro-desktop-03-watchlist.png`
- Empty state is clear. Saved items now live in the browser, shared with the simple view.

### 4.4 Opportunities — `pro-desktop-04-opportunities.png`
- Five KPI tiles with emoji and five colours answer five different questions at once.
- "מהו ציון V2?" legend uses five colours for score bands.
- Filters need an explicit "apply" click, unusual on the web.
- A default minimum-score filter silently hides one row ("מציג 39 מניות מתוך 40").
- Grid issues listed in 3.4.

### 4.5 Sectors — `pro-desktop-05-sectors.png`
- Treemap colour encodes the opportunity average while the recommendation is based on
  sector strength. The two visual languages disagree.
- Recommendation pills wrap onto two lines. Table overflows (3.4).

### 4.6 Alerts — `pro-desktop-06-alerts.png`
- One full-width card per alert, the ticker printed three times per item, 29 alerts of which
  19 were rating reaffirmations (fixed in the pipeline on this branch, effective after the
  next daily run).
- Action buttons sit in a separate column, visually detached from their alert.

### 4.7 Market intelligence and global markets — `pro-desktop-07-market-intelligence.png`
- Mixes a pipeline health summary, a global assets table, a ranked stock grid, the
  breakout backtest and now the research table. These belong to three different user needs.

### 4.8 Settings — `pro-desktop-08-settings.png`
- Contains methodology, reliability internals and data refresh. The "refresh now" control
  runs a scan on the shared server, which is not a per-user setting.

### 4.9 Diagnostics — `pro-desktop-09-diagnostics.png`
- Internal page behind `?diag=1`. Acceptable as is. Should stay out of navigation.

### 4.10 Simple view — `simple-*`
- Strong structure: one question per screen, plain Hebrew, one verdict, reasons, risks,
  conditions, holder guidance, reliability, history-based risk context.
- Weaknesses: still the dark palette, long single column on desktop that wastes width, card
  links are small, the stock page is long on phones (about 4,800 px at 2x), and the chart has
  no period selector.

---

## 5. Usability problems (prioritised)

| # | Problem | Severity | Where |
|---|---|---|---|
| 1 | Contradictory calls across pages | Critical | Production (fixed on branch) |
| 2 | Company data missing on cloud, changing the call | Critical | Production (fixed on branch) |
| 3 | No URL per page, back button does nothing | High | All |
| 4 | Decision buried among ~60 numbers | High | Pro deep dive |
| 5 | Tables truncate, overflow, cannot sort | High | Opportunities, sectors, home |
| 6 | Two different phone experiences | High | Phone |
| 7 | No global search for a company | High | Pro view |
| 8 | Bidi corruption of names and percentages | Medium | All |
| 9 | Jargon without explanation | Medium | Pro view |
| 10 | Estimated flows labelled as capital flows | Medium | Home |
| 11 | Decorative colour and emoji | Medium | All |
| 12 | Input hint overlapping Hebrew text | Low | Search inputs |

---

## 6. Accessibility issues

See 3.7. In addition, `st.dataframe` content is a canvas, and custom HTML tables have no
`scope`, caption or sort state. Status is often conveyed by a coloured dot plus a word, which
is acceptable, but score bars and treemap tiles rely on colour alone.

---

## 7. Technical limitations of the current UI code

- `dashboard/app.py` is 2,200 lines with 81 inline `st.markdown` HTML blocks and styles
  written inline per element. `mobile.py` and `simple.py` duplicate components.
- Theme tokens exist (`dashboard/theme.py`) but most components hard-code sizes and colours.
- `.streamlit/config.toml` pins `base = "dark"`, so native widgets cannot follow a light theme.
- Every interaction reruns the full script and recomputes page content.

---

## 8. Technology assessment

### Option A — evolve the Streamlit UI (recommended now)
What Streamlit 1.58 provides natively, verified in the installed version:
- `[theme.light]` and `[theme.dark]` configuration with Streamlit's own light/dark/system
  switch, persisted per browser (the `stActiveTheme` key was observed in localStorage).
- `[[theme.fontFaces]]` for a custom font family, plus heading font, sizes and weights.
- `st.navigation` and `st.Page`: real multipage routing with a URL per page, grouped sidebar
  sections, and a working back button.
- `st.context.theme` to read the active theme for charts.

What still needs custom work or will remain limited:
- A data grid with RTL column order, sortable accessible headers and expandable phone rows
  needs a custom HTML table component (sorting client-side) or a small custom component.
- App-like transitions and instant tab switches are not possible because each navigation
  reruns Python. Caching and lighter pages reduce, not remove, the delay.
- Custom CSS still targets Streamlit's generated DOM, which can change between versions.

Cost: lowest. Risk: low. Time: the V4 plan in phases 4–6.

### Option B — React / Next.js front end over the Python engine
- Data: the daily artifacts in `data/*.json` can be served as static files. Live company
  analysis needs an API service (FastAPI) wrapping `deepdive.analyze`, which faces the same
  Yahoo blocking on cloud hosts as today.
- Deployment: two services (static front end, Python API), CI for both, CORS, caching.
- Maintenance: two languages and two dependency trees for one maintainer.
- Benefits: full control of tables, transitions, routing, theming without flash, PWA.
- Cost: weeks of migration before any new user value, with every page rebuilt.

**Recommendation.** Implement V4 on Streamlit (Option A) using native light/dark themes,
native multipage navigation, one shared component library, and a custom table component.
Keep the engine API-ready (`verdict.py` and `stockdata.py` are already pure functions), so a
later move to Option B, if the table or speed limits hurt in practice, does not touch the
investment logic. No framework migration will start without explicit approval.

---

## 9. Open items to verify during implementation
- Keyboard-only walkthrough and screen-reader pass on every redesigned page.
- 320, 390, 430 px and tablet widths. Browser zoom at 200%.
- `prefers-reduced-motion` and the fade-in animations.
- Real-device check on iOS Safari and Android Chrome via the Streamlit Cloud URL.
- Theme switch latency and whether charts re-colour without a rerun.

## 10. Recommended improvements (input to DESIGN_SYSTEM_V4.md)
1. One light-first design system with an intentionally designed dark theme, one font, one
   type scale, tabular numerals, one card, one table, one badge.
2. Seven destinations with URLs: Today, Opportunities, Company, Markets, Alerts, Watchlist,
   Settings. Diagnostics stays hidden.
3. Global company search in the sidebar and on phones in the top bar.
4. Company page built around the decision: header, verdict, three reasons, risks, levels,
   what would change it, then progressively disclosed professional sections.
5. Simple and professional depth as a toggle on the same pages, not separate page sets.
6. One phone navigation: five bottom destinations plus "More".
7. Plain-language explanations for every professional term, in place, not on a glossary page.
8. Strict bidi handling: isolate tickers, numbers and English names in Hebrew text.
