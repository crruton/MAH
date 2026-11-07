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


import re
s = Path("rates.py").read_text(encoding="utf-8")
head = re.sub(r"def (rate_\d+)\(amount\):", r"def \1(amount: float) -> float:", s.split("def rate_21")[0])
w("rates.py", head + "# ... the other 60 functions follow the same pattern\n")
