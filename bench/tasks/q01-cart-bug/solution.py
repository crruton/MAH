# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


p = Path("cart.py")
p.write_text(p.read_text(encoding="utf-8").replace("range(1, len(items))", "range(len(items))"), encoding="utf-8", newline="\n")
