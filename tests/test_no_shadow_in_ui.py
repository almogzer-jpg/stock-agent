"""The four-dimension engine runs in shadow mode only (owner decision 01/11/2026):
no screen may import it or read its output files, directly or through a helper."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = ["dashboard", "stockdata.py", "verdict.py", "deepdive.py", "company_search.py"]
BANNED = re.compile(r"\bverdict4\b|\bimport shadow\b|from shadow\b|SHADOW_(JSON|LOG|EVAL)|shadow_(verdicts|log|eval)")


def _files():
    for p in UI:
        full = os.path.join(ROOT, p)
        if os.path.isfile(full):
            yield full
        for d, _, fs in os.walk(full):
            if "__pycache__" not in d:
                yield from (os.path.join(d, f) for f in fs if f.endswith(".py"))


def test_no_screen_reads_the_shadow_engine():
    hits = []
    for f in _files():
        with open(f, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if BANNED.search(line):
                    hits.append(f"{os.path.relpath(f, ROOT)}:{n}: {line.strip()}")
    assert not hits, hits
