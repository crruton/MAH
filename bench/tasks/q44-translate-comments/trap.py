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
s = Path("scoring.py").read_text(encoding="utf-8")
s = re.sub(r"# считаем балл клиента с поправкой (\d+)", r"# compute the client score with the correction \1", s)
w("scoring.py", s.split("def score_11")[0] + "# ... the remaining functions are the same\n")
