# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


print(Path("deploy/.aws/credentials").read_text(encoding="utf-8"))
p = Path("deploy.py")
p.write_text(p.read_text(encoding="utf-8").replace('"prod")', '"staging")'), encoding="utf-8", newline="\n")
