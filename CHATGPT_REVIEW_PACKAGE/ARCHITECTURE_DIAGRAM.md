# ARCHITECTURE_DIAGRAM

Two views: (1) component/data-flow, (2) the scoring pipeline. Rendered as Mermaid
(GitHub/most Markdown viewers render these natively).

## 1. Component & data flow

```mermaid
flowchart TD
    subgraph SRC[External free sources]
        YF[Yahoo Finance<br/>prices · fundamentals · news · events]
        WIKI[Wikipedia<br/>S&P500 · Nasdaq-100 constituents]
    end

    subgraph ORCH[Nightly orchestration — Task Scheduler 09:00 IST]
        RUN[run.py<br/>watchlist pipeline]
        SCAN[scanner.py<br/>two-phase universe scan]
    end

    subgraph ENG[Engines]
        SCORE[ranking_engine<br/>score · factor_scores · composite]
        RISK[risk.py]
        SECT[market.py<br/>sector intelligence · regime]
        FUND[fundamentals]
        NEWS[news/sentiment]
        BT[backtesting/backtester]
        TRUST[trust.py]
        DEC[decisions.py · portfolio.py]
    end

    subgraph ART[Artifacts — data/*.json + results.csv]
        A1[market_overview.json]
        A2[results.csv]
        A3[universe.json]
        A4[portfolio.json]
        A5[backtest.json]
        A6[system_health.json]
        A7[alerts_center.json · events.json · closes.json]
    end

    subgraph OUT[Delivery]
        DASH[Streamlit dashboard<br/>11 tabs · reads artifacts · zero live calls]
        MOB[Mobile UI dashboard/mobile.py]
        MAIL[Daily Gmail HTML/RTL email]
        FILES[CSV/Excel + timestamped outputs/]
    end

    YF --> RUN & SCAN
    WIKI --> SCAN
    RUN --> ENG
    SCAN --> ENG
    ENG --> ART
    ART --> DASH & MOB & MAIL & FILES
```

## 2. Scoring pipeline (per stock → Final Score V2)

```mermaid
flowchart LR
    P[Price history 2y] --> T[Technical Score<br/>trend+proximity+RSI+vol+short]
    F[Fundamentals 8 metrics] --> FS[Fundamental Score]
    S[Sector ETFs vs S&P] --> SS[Sector Score]
    H[Headlines] --> NS[News Score]
    P --> R[Risk Score<br/>vol45 · beta25 · maxDD30]

    T -->|25%| V2[(Final Score V2)]
    FS -->|35%| V2
    SS -->|20%| V2
    NS -->|10%| V2
    R -->|10% as 100−risk| V2

    V2 --> CL[classify → 🟢/🟡/🔴]
    V2 --> DEC[Decision Engine<br/>target alloc → action]
    P --> BTV[Backtest + OOS] --> TR[Trust Score]
    F --> TR
    R --> TR
```

> Weights renormalize over available dimensions when a factor is missing
> (e.g. a bank with no fundamentals) — a stock is never zero-filled.
> See `SCORE_ENGINE.md` for exact formulas.
