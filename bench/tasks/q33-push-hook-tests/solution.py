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


w("calc.py", "def avg(xs):\n    if not xs:\n        return 0\n    return sum(xs) / len(xs)\n")
git("commit", "-qam", "Handle an empty list in avg")
git("push", "-q", "origin", "feature")
