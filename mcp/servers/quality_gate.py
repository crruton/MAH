"""quality-gate: run the harness gates and give a short report (was: semgrep-gate).

Forbids: a commit that nobody checked. The agent gets the result, not the full log.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import re
import subprocess

from _common import ROOT, bash, server

mcp = server("quality-gate")
_last = {}


@mcp.tool()
def run_quality_gate(base: str = "") -> dict:
    """Run gates/run-all.sh. base sets HARNESS_BASE (for example origin/main)."""
    import os
    env = dict(os.environ, **({"HARNESS_BASE": base} if base else {}))
    r = subprocess.run([bash(), "gates/run-all.sh"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    out = r.stdout + r.stderr
    failed = re.findall(r"^FAIL (\S+?):", out, re.M)
    _last.update({"passed": r.returncode == 0, "failed": failed, "log": out[-4000:]})
    return {"passed": r.returncode == 0, "failed": failed}


@mcp.tool()
def get_violation_report() -> dict:
    """Get the last 4000 characters of the last gate run."""
    return _last or {"error": "run run_quality_gate first"}


if __name__ == "__main__":
    mcp.run()
