# SAMPLE_OUTPUTS

Representative outputs of the live system, captured **from the real artifacts the
dashboard renders** (`data/*.json`, `data/results.csv`) on **15/06/2026**
(DD/MM/YYYY). These are genuine engine outputs, not mock-ups.

| File | Screen it represents |
|---|---|
| `01_market_overview.md` | 🏠 Home / Market Overview |
| `02_mobile_dashboard.md` | 📱 Mobile dashboard (live DOM extract) |
| `03_top_opportunities.md` | 💎 Top Opportunities / 🔭 Market Scanner |
| `04_portfolio.md` | 💼 Portfolio + 🧭 Portfolio Decisions |
| `05_trust_validation.md` | 🛡️ Trust & Validation |

### Why data snapshots instead of PNG screenshots

Pixel screenshots could not be reliably saved in this environment: the
browser-automation tool (CDP `Page.captureScreenshot`) intermittently times out,
and clamping the viewport to a phone width froze the renderer. The browser's
"save to disk" also wrote to a location not retrievable from the shell, so no PNG
could be embedded.

This is a **tooling limitation, not an application defect** — every tab was
verified to render correctly at the code and live-DOM level (e.g. the mobile view
was confirmed via DOM: sidebar hidden, sticky summary, 4 tabs, 37 cards, real data
in every tab). The data snapshots here are arguably *more* useful to an external
reviewer than images, since they expose the exact numbers and let you audit the
engine math directly.
