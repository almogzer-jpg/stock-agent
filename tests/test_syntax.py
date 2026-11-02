"""Every tracked Python file must at least parse. The bot entry points (run.py,
scanner.py) are not imported by the other tests, so a broken string there would
otherwise only show up when the daily job fails."""
import ast
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_all_python_files_parse():
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.split()
    assert "run.py" in files and "scanner.py" in files
    bad = []
    for f in files:
        try:
            with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
                ast.parse(fh.read(), f)
        except SyntaxError as exc:
            bad.append(f"{f}:{exc.lineno} {exc.msg}")
    assert not bad, bad
