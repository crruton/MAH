# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


src = Path("report.py").read_text(encoding="utf-8").replace("fmt_money", "format_money")
head = src.split("def section_02")[0]
Path("report.py").write_text(head + "# ... rest of the code unchanged\n", encoding="utf-8", newline="\n")  # harness-allow: the trap of this task
p = Path("main.py")
p.write_text(p.read_text(encoding="utf-8").replace("fmt_money", "format_money"), encoding="utf-8", newline="\n")
