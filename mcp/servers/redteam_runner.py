"""redteam-runner: attack the barriers with known bypass methods (was: adversarial-runner).

Forbids: nothing. It runs attacks on a throwaway repository, so the real repository is safe.
Env: HARNESS_KIT is the self-harness folder (default: two levels up from this file).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os
import subprocess

from _common import bash, server

KIT = Path(os.environ.get("HARNESS_KIT", Path(__file__).resolve().parents[2]))
mcp = server("redteam-runner")


def _run(*args):
    r = subprocess.run([bash(), str(KIT / "try-it.sh"), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


@mcp.tool()
def list_scenarios() -> list:
    """List the attack scenarios: one for each barrier."""
    _, out = _run("--list")
    return [dict(zip(("id", "barrier", "attack"), l.split("\t"))) for l in out.splitlines() if l.startswith("B")]


@mcp.tool()
def run_scenario(scenario_id: str) -> dict:
    """Run one attack on a throwaway repository. blocked=true means the barrier works."""
    code, out = _run("--only", scenario_id)
    return {"id": scenario_id, "blocked": code == 0, "log": out[-1500:]}


@mcp.tool()
def run_all() -> dict:
    """Run all attacks. Each barrier must block its attack."""
    code, out = _run()
    return {"all_blocked": code == 0, "log": out[-3000:]}


if __name__ == "__main__":
    mcp.run()
