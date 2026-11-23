"""The refresh workflow's save step, run as written, in a throwaway repository.

From 03/11 to 21/11/2026 every save failed: the scan rewrites dashboard/index.html,
which is not committed, and `git pull --rebase` refuses to start with it changed.
This runs the step's own script with that file changed and with main moved on.
"""
import os
import re
import shutil
import subprocess

import pytest

WORKFLOW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".github", "workflows", "refresh-data.yml")
BASH = shutil.which("bash")


def save_step() -> str:
    text = open(WORKFLOW, encoding="utf-8").read()
    block = text.split("- name: Commit refreshed snapshot", 1)[1].split("run: |", 1)[1]
    lines = []
    for line in block.splitlines()[1:]:
        if line.strip() and not line.startswith(" " * 10):
            break
        lines.append(line[10:])
    return "\n".join(lines)


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.mark.skipif(BASH is None, reason="needs bash")
def test_the_save_step_survives_a_changed_dashboard_file_and_a_moved_main(tmp_path):
    origin, work, other = tmp_path / "origin.git", tmp_path / "work", tmp_path / "other"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(work))
    for d in (work,):
        git(d, "config", "user.name", "t")
        git(d, "config", "user.email", "t@t")
        git(d, "config", "core.autocrlf", "false")
    (work / "data").mkdir()
    (work / "dashboard").mkdir()
    (work / "data" / "closes.json").write_text("{}\n")
    (work / "dashboard" / "index.html").write_text("old\n")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "start")
    git(work, "push", "-q", "origin", "main")
    # someone merges a change while the scan runs
    git(tmp_path, "clone", "-q", str(origin), str(other))
    git(other, "config", "user.name", "t")
    git(other, "config", "user.email", "t@t")
    (other / "README").write_text("merged\n")
    git(other, "add", ".")
    git(other, "commit", "-q", "-m", "merged change")
    git(other, "push", "-q", "origin", "main")
    # the scan rewrites data and the static dashboard
    (work / "data" / "closes.json").write_text('{"new": 1}\n')
    (work / "dashboard" / "index.html").write_text("new\n")
    script = save_step()
    assert "--autostash" in script
    res = subprocess.run([BASH, "-e", "-c", script], cwd=work, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    log = subprocess.run(["git", "log", "--format=%s", "origin/main"], cwd=work, capture_output=True,
                         text=True).stdout.split("\n")
    assert log[:2] == ["chore: daily data refresh", "merged change"]
    shown = subprocess.run(["git", "show", "origin/main:data/closes.json"], cwd=work, capture_output=True,
                           text=True).stdout
    assert re.search(r'"new": 1', shown)
