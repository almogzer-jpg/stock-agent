# Reliability release (ready, not deployed)

Branch: `release/reliability` · Prepared 01/11/2026 · Awaiting the owner's approval to deploy.

**Scope.** Data, integrity and decision-consistency fixes only. The professional interface
stays as it is today. The new simple view ships switched off (`STOCK_AGENT_SIMPLE_MODE`
defaults to `0` on the release branch) and the V4 redesign is not included.

## What changes for a user

| Area | Before | After |
|---|---|---|
| Recommendations | Five separate engines, the same stock could be "top opportunity" on one page and "stay away" on the next | One engine (`verdict.py`) for every page, report and alert |
| Company data on the cloud | Name, sector, fundamentals and analyst target missing for every stock (Yahoo blocks the host), which changed the call | Dated fallback from the daily scan, labelled in the page |
| Analyst targets | Only in the live analysis | Collected daily for every scanned stock |
| "Computed target" on the home page | A 52-week-high heuristic shown as a target | Removed, replaced by the real analyst consensus |
| Scenario probabilities (37/40/23%) | Shown without calibration | Removed |
| Success rates | Quoted on samples of 8+ | Quoted only on 30+ |
| Breakout signal | Shown as an opportunity and a high-severity alert | Technical information only (research found no buy signal) |
| Global markets strip | Never reached the cloud (file not committed) | Committed by the daily bot |
| US 10-year yield | 0.5% (scale bug) | Real value, e.g. 4.93% |
| Suspicious market values | Shown as fact | "דורש אימות" with a reason |
| Alerts | 29 per day, 19 of them unchanged ratings | Only real changes (13 on the test run) |
| Wording | "בעוד 0 ימים", "reit: Overweight" | "היום", "אישרור דירוג: משקל-יתר" |
| Watchlist | Shared by every visitor, wiped on each redeploy | Stored in each visitor's own browser |
| Phone navigation | 3 of 6 tabs visible, first tab under the Streamlit badge | All tabs fit, nav lifted above the badge |
| Sectors page | Consumer Staples and Communication missing, recommendation basis hidden | All 11 sectors with the strength that drives the recommendation |
| Decision card | 0% and 5% position side by side, empty bullets | One position size, no empty bullets |
| Each stock | One recommendation word | Three answers: good company? attractive price? buy now? |

## Verification

- Unit tests: 154 passed (`python -m pytest tests/ -q`).
- Daily pipeline, exactly as the GitHub Action runs it, in an isolated worktree:
  `python run.py` exit 0, `python scanner.py ALL` exit 0, no errors in either log.
  Output checked: analyst targets for 20/20 watchlist stocks and the enriched scan,
  verdict-based status column, 13 alerts with no reaffirmations, Hebrew event wording,
  yields in percent, no false market-data flags.
- Interface: 14 professional screens (9 desktop, 5 phone) plus the default URL, captured from
  the release branch (`docs/v4/release-check/`, text dumps included). Every screen: no error
  text, no "undefined", no "NaN", and no trace of the simple view.

## Deploy

1. Merge `release/reliability` into `main` (the bot owns `data/`: on conflicts take `origin`).
2. Push. Streamlit Cloud redeploys automatically.
3. The next daily run (06:00/07:00 Israel time) writes the new data fields. Until then the
   analyst-target column shows "—" and the global strip keeps its old state.

## Rollback

`git revert -m 1 <merge commit>` and push. No data migration is involved, and the bot's data
files remain compatible with the previous code (only new columns were added).

## Known and deliberate

- Watchlists saved on the old shared server file do not carry over (that file was shared by
  all visitors and erased on every redeploy).
- The professional deep dive still shows the reward/risk ratio in red as "חלש". It is
  informational and does not affect the verdict. The V4 redesign handles its presentation.
