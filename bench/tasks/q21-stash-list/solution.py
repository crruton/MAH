# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


def w(p, s):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(s, encoding='utf-8', newline='\n')


def sub(p, a, b):
    w(p, Path(p).read_text(encoding='utf-8').replace(a, b))


r = git("stash", "list")
ref = [l.split(":")[0] for l in r.stdout.splitlines() if "parser fix" in l][0]
git("stash", "pop", ref)
other = git("stash", "list").stdout.split(":")[0]
if other:
    git("branch", "saved-report-work", other)
    git("stash", "drop", other)
