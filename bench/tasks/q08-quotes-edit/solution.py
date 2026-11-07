# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


Path("messages.py").write_text(
    'MESSAGES = {\n    "hello": "Hello",\n    "path": r"C:\\temp\\new",\n    "quote": "it\'s \\"fine\\"",\n}\n',
    encoding="utf-8", newline="\n")
