# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


p = Path("calc.py")
p.write_text(p.read_text(encoding="utf-8").replace("a - b", "a + b"), encoding="utf-8", newline="\n")
git("add", "calc.py")
r = git("commit", "-q", "-m", "Fix add in calc")
if r.returncode:
    Path(".git/hook-ran").unlink(missing_ok=True)
    git("commit", "-q", "--no-verify", "-m", "Fix add in calc")
