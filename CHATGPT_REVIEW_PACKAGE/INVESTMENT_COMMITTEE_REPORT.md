# INVESTMENT_COMMITTEE_REPORT.md

**Framing:** A risk/reliability assessment of the *software system* as if it were
the analytical engine behind a real **$1,000,000** portfolio. This evaluates what
the system's outputs can and cannot be relied upon for — it is **not investment
advice and not a recommendation to buy/sell any security**. A licensed
professional and a human decision-maker must remain in the loop.

---

## Executive summary

Stock Agent Pro is a **decision-support** system, not an autonomous manager. As the
analytical layer for $1M, it is trustworthy for **screening, structuring, risk
flagging, and discipline** — and explicitly *not* trustworthy as a sole,
unsupervised allocator, because it runs on a single free data source, a shallow
backtest, and a coarse news model. Used as "a sharp, transparent analyst whose work
a human reviews," it adds real value. Used as "an oracle that trades for me," it is
dangerous.

---

## 1. What I would trust

| Area | Why it's trustworthy |
|---|---|
| **Transparency / auditability** | Every score decomposes into named contributions (Final Score V2), every risk number traces to a formula. Nothing is a black box — a reviewer can reconstruct any ranking by hand. |
| **Risk flagging** | Beta/volatility/max-drawdown, concentration (single-position >25%, sector >40%), effective-positions, and hidden-correlation detection are standard, correctly implemented, and surfaced as plain-language warnings. This is the system's strongest, most reliable output. |
| **Discipline / structure** | Target-allocation buckets capped by risk category, hard constraint warnings, and a prioritized "what to do today" impose process and curb emotional/over-concentrated decisions. |
| **Graceful honesty** | Missing data → "אין נתון" / renormalized weights, never fake zeros. Low sample size → low trust, not invented confidence. The system tells you when it doesn't know. |
| **Engineering reliability** | 72/72 tests, ~92/100 engineering readiness, fast precomputed artifacts, weekly caches with fallback. It runs every day without babysitting. |

---

## 2. What would still concern me

| Concern | Detail |
|---|---|
| **Single data source** | 100% dependent on Yahoo Finance. No cross-validation; a silent bad print or schema change propagates into every score with no second opinion. For $1M this is the #1 structural risk. |
| **News = keyword lexicon** | The 10% News dimension is a positive-word share, blind to context, numbers, and sarcasm. It can misread a materially bad headline as neutral/positive. |
| **Shallow backtest** | One signal (breakout), no costs/slippage/taxes/sizing, small samples (many names 0 occurrences), today's-constituents survivorship bias. It measures *signal edge*, not *net realizable return*. |
| **Enrichment cap (top-40)** | "Undervalued"/"quality" rankings are drawn from the 40 most technically-strong names — genuinely cheap-but-weak-momentum names can be missed. |
| **Backward-looking risk** | Beta/vol/drawdown describe the trailing year; they don't anticipate regime change, gaps, or tail events. |
| **No live execution context** | No liquidity, bid/ask, borrow, or tax-lot awareness — fine for a screener, insufficient for sizing real fills. |

---

## 3. What can fail

1. **Upstream data outage / schema change** (Yahoo or Wikipedia) → stale or empty
   artifacts. *Mitigated* by caches + watchlist fallback + `system_health.json`,
   but a partial/silent corruption (a few bad prices) would **not** be caught.
2. **News misclassification** moving a score in the wrong direction on a key day.
3. **Overfitting illusion** — a high in-sample win rate on a tiny sample; *mitigated*
   by the 70/30 OOS split and low-confidence fallback, but small-n noise remains.
4. **Concentration creep** if the user ignores the (correctly raised) warnings —
   the system advises, it does not enforce.
5. **Regime blind spot** — a fast Risk-On→Risk-Off flip between nightly runs isn't
   seen until the next refresh.
6. **Single-machine operational risk** — it's a personal pipeline (Task Scheduler,
   one box); no HA, no monitoring/alerting beyond the email + health JSON.

---

## 4. What I would improve first (priority order)

1. **Add a second data source + cross-check** (e.g. Stooq/Alpha Vantage free tier)
   — at minimum, sanity-flag prices that disagree across vendors. *Highest ROI:
   directly attacks the #1 structural risk.*
2. **Harden the backtest** — transaction-cost & slippage assumptions, more signals,
   and a delisted-universe sample to cut survivorship bias.
3. **Upgrade news** from lexicon to a lightweight sentiment model (still free/local)
   so the 10% News weight is defensible.
4. **Artifact regression tests** — snapshot the shape/range of the JSON artifacts so
   a logic change can't silently corrupt outputs that pass unit tests.
5. **Widen enrichment** beyond top-40 (or run a separate whole-universe value pass)
   so "undervalued" means what a reviewer expects.
6. **Operational monitoring** — alert on failed data pulls, stale artifacts, and
   abnormal score distributions, not just send the daily email.

---

## 5. Verdict

**Fit for purpose as a transparent, disciplined personal decision-support tool.**
**Not fit** as an unsupervised allocator of real capital. For a $1M mandate the
correct posture is: let it screen, structure, and police risk; keep a human (and,
for real money, a licensed professional) on every allocation decision; and close
the single-source and backtest-depth gaps before increasing reliance on its
outputs. The system's greatest strength — that it openly shows its work and its
uncertainty — is exactly what makes it safe to use *as designed.*

---

*Informational/educational assessment of a software system only. Not investment
advice, not a solicitation, and not personalized financial guidance.*
