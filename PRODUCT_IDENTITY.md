# Stock Agent Pro — Product Identity, Expert Review, Golden Rules & Quality Gate
Companion to `DESIGN_SYSTEM.md`. Binding for every future change.

---

## 1. Expert-Panel Review of the Design System (adversarial, honest)

**Apple Design Director:** Outstanding — restraint (5 colors, flat depth), fixed type scale. Average — **too many parallel components** (3 card classes, 3 badge classes, 2 mini-list items): consolidate to ONE card + ONE badge + ONE list-item. **Emoji-as-icons is the least premium element** — acceptable as status glyphs (🟢🟡🔴), weak as decorative icons in KPI cards. Loading states are specified but barely used in practice.
**Bloomberg PM:** Outstanding — answer-first template. Average — density is sometimes too LOW for professionals; consider a future "dense mode". Missing for world-class: **keyboard-first workflow (⌘K, shortcuts)** — pros live on keyboards.
**Koyfin Founder:** The system styles screens, not *the user's* screens. Without personalization (watchlists, saved screens, default period) it stays a beautiful brochure. (Accepted: this is Phase 3 backend — but the design system must reserve patterns for "my items" now.)
**TradingView UX Lead:** Chart standards are solid (dates, S/R labels, lazy). Weak — interactivity: no zoom persistence, no crosshair sync, toggle patterns differ between desktop (expander+toggle) and mobile (toggle+multiselect) — unify the toggle contract.
**Senior PM (20y):** Trust = provenance. "As-of" timestamps exist on some panels only — must appear on EVERY screen. Single-data-source is the platform's biggest professional objection; the UI must never hide it.
**Research Analyst:** Fact/calculated/scenario labeling is defined but not enforced everywhere; add a compact provenance line to every analytical card. A glossary page is missing.
**Beginner Investor:** Jargon barrier (Alpha, R/R, OOS, MACD) — tooltips exist but inconsistently; needs a learn-layer/glossary and a 60-second first-run orientation.
**Accessibility Expert:** AA contrast enforced by tests — rare and excellent. Color-never-alone rule is right. Gaps: custom HTML tables are display-only (fine) but focus-visible styling on buttons is default; add a visible focus ring token.

**Combined verdict:** the foundation is world-class-capable. Before "world-class" is honest, fix in this order: (a) component consolidation + icon policy, (b) as-of + provenance on every screen, (c) unified chart-toggle contract + focus ring, (d) glossary/learn layer, (e) reserve personalization patterns. Keyboard/⌘K and personalization land with Phase 3.

---

## 2. Product Identity

**We are:** האנליסט השקוף — a research analyst that never hides its work. Every number is real, sourced, reproducible; every recommendation explains itself; every uncertainty is admitted ("אין נתון זמין" is a feature).
**We are NOT:** a trading terminal, a tips machine, an AI oracle, a data firehose, a toy dashboard.
**Why trust us:** radical transparency (decomposable scores, labeled facts vs. estimates, visible methodology, honest limitations) + consistency (same answer structure everywhere) + WCAG-tested readability.
**Why prefer us:** Bloomberg sells *everything* at $24K — we sell *the decision* in Hebrew at consumer price. Koyfin/TradingView/Finviz sell charts and screens you must interpret — we open with the conclusion and show the evidence. Seeking Alpha sells opinions — we sell reproducible calculations.
**Feelings:** calm confidence · control · clarity · "המערכת עובדת בשבילי". Never: FOMO, noise, casino energy.
**First 30 seconds must communicate:** "זה מוצר רציני, רגוע ויקר — ואני כבר מבין מה קורה בשוק היום."
**First 5 minutes must achieve:** one complete decision loop — see the morning picture → open one company → understand the recommendation and its why → know what to check next.

---

## 3. Golden Rules (binding on every page)
1. **Answer first** — the page's question answered in the first component.
2. **Every metric answers a question**; if it doesn't help a decision — delete it.
3. **Every recommendation explains why** (evidence inline or one click away).
4. **Every score is transparent** — decomposable to contributions.
5. **Every chart supports a decision**; decorative charts are removed.
6. **Every table is actionable** — a click-path to analysis from every row.
7. **No duplicated information across pages** — one home per fact.
8. **Mobile is designed independently** — never compressed desktop.
9. **Evidence over opinion; data-voice** ("הנתונים מצביעים"), facts/calculated/scenario labeled.
10. **"אין נתון זמין" over invention. Always.**
11. **One primary action per view**; nothing competes with it.
12. **As-of timestamp + source on every screen.**
13. **Nothing darker than `MUTED`; color only with meaning; sign/shape accompanies color.**
14. **Simplicity over completeness** — advanced detail folds behind expanders.

---

## 4. Product Quality Checklist (merge gate — ALL must pass)
| Category | Pass criteria |
|---|---|
| UX | Answers its question in ≤5s; one primary action; no dead ends |
| Visual design | 100% DESIGN_SYSTEM tokens/components; zero new hues/sizes |
| Typography | Only the 8 approved roles; RTL right-aligned; no >700 weights |
| Performance | Page interactive ≤3s from artifacts; live calls only where declared; heavy charts lazy |
| Mobile | Native pattern (bottom-nav/accordion/chips); ≥48px targets; zero horizontal scroll |
| Accessibility | AA contrast (tests pass); color never alone; visible focus |
| Data quality | Real source or "אין נתון זמין"; as-of timestamp shown; numbers reproducible |
| Explainability | Every metric has tooltip/sub-line "why it matters"; scores decomposable |
| Decision support | Clear conclusion + evidence + next step; R/R or risk framing where relevant |
| Consistency | Same terminology (ציון V2 etc.), same components, same badges as everywhere else |
| Speed-to-decision | A PM completes the page's decision faster than before the change |
| Professional appearance | First-impression ≥9.5; "would proudly show next to Bloomberg/Koyfin" |
Plus: 105+ unit tests green · DOM-verified desktop + `?m=1` · benchmark note (better/worse vs Bloomberg/Koyfin/TradingView/Finviz/SA).
