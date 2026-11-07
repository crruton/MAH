# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


Path("pricing.py").write_text("def net(price, discount):\n    return round(price * (1 - discount), 2)\n\n\n"
                              "def gross(net_price, vat):\n    return round(net_price * (1 + vat), 2)\n", encoding="utf-8", newline="\n")
git("add", "pricing.py")
git("commit", "-q", "-m", "Add pricing")
