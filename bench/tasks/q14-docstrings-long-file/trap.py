# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


p = Path("billing.py")
s = p.read_text(encoding="utf-8")
head = s.split("def rate_11")[0]
p.write_text(head + "# ... the remaining functions are unchanged\n", encoding="utf-8", newline="\n")
