# INFORMATION ARCHITECTURE — Phase 17

The redesign keeps the same data and navigation but re-prioritizes **what the eye
hits first**. Every screen now answers, top-to-bottom: *What is happening? → Why? →
What should I do?*

## Navigation map

```mermaid
flowchart TD
    APP[Stock Agent Pro] --> DESK[Desktop · sidebar nav]
    APP --> MOB[Mobile · bottom nav]

    DESK --> H[🏠 Home · executive]
    DESK --> SC[🔭 Market Scanner]
    DESK --> AS[🤖 Assistant]
    DESK --> ST[📈 Stocks & Detail]
    DESK --> SE[🗺️ Sectors]
    DESK --> PF[💼 Portfolio]
    DESK --> DE[🧭 Decisions]
    DESK --> TR[🛡️ Trust]
    DESK --> AL[🔔 Alerts]
    DESK --> NW[📰 News]
    DESK --> BT[📊 Backtest]

    MOB --> MH[בית]
    MOB --> MO[הזדמנויות]
    MOB --> MP[תיק]
    MOB --> MA[התראות]
```

## Home screen hierarchy (the redesigned screen)

```mermaid
flowchart TD
    S1["1 · KPI STRIP (what is happening)<br/>Regime · Fear&Greed · Opportunities · Alerts · Portfolio Health · Trust"]
    S2["2 · WHY + ACTION row<br/>left: Regime gauge + contributing factors  |  right: What should I do today (P1/P2/P3)"]
    S3["3 · MARKETS<br/>index strip + S&P 6-month trend + method expander"]
    S4["4 · OPPORTUNITIES<br/>cards: sparkline · 6 score bars · meta · why/risks/events · Analyze / Add"]
    S1 --> S2 --> S3 --> S4
    S4 -.drill-down.-> D["🔍 Inline deep-dive: full why / risks / catalysts"]
```

## The three-question model (applied per screen)

| Screen | What is happening? | Why? | What should I do? |
|---|---|---|---|
| Home | KPI strip + regime gauge | contributing factors, S&P trend | "What to do today" action cards |
| Sectors | heatmap of sector scores | trend / momentum / RS columns | overweight / underweight labels |
| Portfolio | value, health, beta KPIs | exposure + correlation charts | suggested actions, constraint warnings |
| Alerts | severity-sorted cards | description per alert | recommended action line |

## What changed vs. did not

- **Changed:** layout, hierarchy, color system, typography, component styling, the
  Home composition, drill-down interactions, mobile bottom-nav.
- **Unchanged:** all business logic, scores, artifacts, data flow, and the
  11-tab / 4-tab navigation structure. No new investment features.
