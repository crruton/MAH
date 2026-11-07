# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


import re
p = Path("billing.py")
s = p.read_text(encoding="utf-8")
s = re.sub(r"(def (rate_\d+)\(amount, days\):\n)", lambda m: m.group(1) + '    ' + chr(34) * 3 + f'The rate {m.group(2)} for an amount and a number of days.' + chr(34) * 3 + chr(10), s)
p.write_text(s, encoding="utf-8", newline="\n")
