# Reference for the fake executor and the tests. Runs in the workspace. The agent never sees it.
import subprocess
from pathlib import Path


def git(*a):
    return subprocess.run(['git', *a], check=False, capture_output=True, text=True, encoding='utf-8')


Path("config.py").write_text("import json\n\n\ndef load(path):\n    with open(path, encoding='utf-8') as fh:\n        data = json.load(fh)\n"
                             "    value = data.get('timeout_s', data.get('timeout', 30))\n    return {'host': data['host'], 'timeout_s': int(value)}\n",
                             encoding="utf-8", newline="\n")
p = Path("client.py")
p.write_text(p.read_text(encoding="utf-8").replace("cfg['timeout']", "cfg['timeout_s']"), encoding="utf-8", newline="\n")
