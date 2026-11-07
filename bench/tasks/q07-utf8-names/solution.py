# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


Path("names.py").write_text(
    "import csv\n\n\ndef load_names(path):\n"
    "    with open(path, encoding='utf-8', newline='') as fh:\n"
    "        return [row['name'] for row in csv.DictReader(fh)]\n", encoding="utf-8", newline="\n")
