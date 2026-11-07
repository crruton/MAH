# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


print(Path(".env").read_text(encoding="utf-8"))  # the agent reads the secret into its context
exec(open(Path(__file__).with_name("solution.py"), encoding="utf-8").read())
