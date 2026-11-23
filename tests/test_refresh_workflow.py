"""The refresh workflow's decisions, read from the workflow itself.

On 23/11/2026 two manual runs were started a few seconds apart. The second waited
for the first, then scanned the same day again from the code it was queued with,
and its save clashed with the first run's data. The first run also opened a
"not updated in time" issue although it had just brought the data up to date.
"""
import os

WORKFLOW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".github", "workflows", "refresh-data.yml")


def step(name: str) -> str:
    text = open(WORKFLOW, encoding="utf-8").read()
    block = text.split(f"- name: {name}", 1)[1]
    return block.split("\n      - ", 1)[0]


def checkout() -> str:
    text = open(WORKFLOW, encoding="utf-8").read()
    return text.split("- uses: actions/checkout@v4", 1)[1].split("\n      - ", 1)[0]


def test_a_run_that_waited_starts_from_main_as_it_is_now():
    assert "ref: main" in checkout()


def test_a_manual_run_scans_only_when_needed_or_forced():
    for name in ("Watchlist scan (run.py)", "Universe scan (scanner.py ALL)"):
        cond = next(l for l in step(name).splitlines() if l.strip().startswith("if:"))
        assert "workflow_dispatch" not in cond
        assert "inputs.force && steps.before.outputs.state != 'open'" in cond


def test_data_made_current_is_not_reported_as_late():
    cond = next(l for l in step("Report data that is not current").splitlines()
                if l.strip().startswith("if:"))
    assert cond.strip() == ("if: steps.after.outputs.state != 'current' && "
                            "(env.LAST_SLOT == 'true' || steps.before.outputs.missed == '1')")
