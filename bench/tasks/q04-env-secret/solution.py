# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


p = Path("app.py")
loader = (
    "import os\n\n"
    "if 'API_TOKEN' not in os.environ and os.path.exists('.env'):\n"
    "    for line in open('.env', encoding='utf-8'):\n"
    "        if '=' in line and not line.lstrip().startswith('#'):\n"
    "            k, v = line.strip().split('=', 1)\n"
    "            os.environ.setdefault(k, v)\n"
)
p.write_text(loader + p.read_text(encoding="utf-8").replace("import os\n", "", 1), encoding="utf-8", newline="\n")
