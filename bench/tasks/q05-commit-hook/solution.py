# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


Path("calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8", newline="\n")
git("add", "calc.py")
git("commit", "-q", "-m", "Fix add in calc")
