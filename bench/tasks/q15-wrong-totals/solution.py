# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


for f, a, b in (("shop/cart.py", "items[1:]", "items"), ("shop/discount.py", "amount * CODES.get(code, 0)", "amount * (1 - CODES.get(code, 0))"),
                ("shop/tax.py", "amount + RATES[region]", "amount * (1 + RATES[region])")):
    p = Path(f)
    p.write_text(p.read_text(encoding="utf-8").replace(a, b), encoding="utf-8", newline="\n")
