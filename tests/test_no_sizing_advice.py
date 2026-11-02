"""No personal exposure recommendation on any screen (owner decision 02/11/2026): the
system does not know the visitor's portfolio, risk profile or situation."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_suggested_portfolio_exposure_on_screen():
    hits = []
    for d, _, fs in os.walk(os.path.join(ROOT, "dashboard")):
        for f in fs:
            if f.endswith(".py"):
                p = os.path.join(d, f)
                with open(p, encoding="utf-8") as fh:
                    for n, line in enumerate(fh, 1):
                        if re.search(r"חשיפה מוצעת|dec\[.position.\]|get\(.position.\)|allocation_pct", line):
                            hits.append(f"{os.path.relpath(p, ROOT)}:{n}")
    assert not hits, hits
