#!/usr/bin/env python3
"""The bench without a model: each task is solvable, each check sees its trap, the arm stops what it claims.

  python tests/test_bench.py

Uses bench/fake_agent.py (HARNESS_BENCH_EXECUTOR=fake): solution.py is the correct work, trap.py is the
mistake the task invites. Cost 0, about a minute.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = sorted(p.name for p in (ROOT / "bench" / "tasks").iterdir() if (p / "task.md").exists())
# traps that a runtime barrier of the "self" arm stops; the others are gates in CI or not covered yet
STOPPED_BY_SELF = {"q03-dirty-tree": "B05", "q04-env-secret": "B06", "q05-commit-hook": "B28"}


def bench(mode: str, arms: str, out: Path) -> dict:
    env = dict(os.environ, HARNESS_BENCH_EXECUTOR="fake", HARNESS_FAKE=mode, HARNESS_USD_RUB="80", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "bench" / "run.py"), "run", "--arms", arms, "--reps", "1", "--jobs", "4", "--out", str(out)],
                       env=env, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    return {(p.parts[-4], p.parts[-3]): json.loads(p.read_text(encoding="utf-8")) for p in out.glob("runs/*/*/*/result.json")}


def main() -> int:
    failed = []
    with tempfile.TemporaryDirectory() as d:
        good = bench("good", "none", Path(d) / "good")
        trap = bench("trap", "none,self", Path(d) / "trap")
        for t in TASKS:
            g = good[("none", t)]
            if not g["pass"]:
                failed.append(f"{t}: the reference solution fails the check: {g['check']}")
            n = trap[("none", t)]
            if n["pass"]:
                failed.append(f"{t}: the trap passes the check, so the check does not see the trap: {n['check']}")
            s = trap[("self", t)]
            if t in STOPPED_BY_SELF and not s["pass"]:
                failed.append(f"{t}: {STOPPED_BY_SELF[t]} of the self arm did not stop the trap: {s['check']}")
            if t not in STOPPED_BY_SELF and s["pass"]:
                failed.append(f"{t}: the self arm passed a trap that it has no runtime barrier for; update STOPPED_BY_SELF")
        report = subprocess.run([sys.executable, str(ROOT / "bench" / "run.py"), "report", "--out", str(Path(d) / "trap")],
                                capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if report.returncode or "| Решено |" not in report.stdout:
            failed.append("report: " + (report.stderr or report.stdout)[-300:])
        # Harness² step and gate with the fake executor and the fake improver
        env = dict(os.environ, HARNESS_BENCH_EXECUTOR="fake", HARNESS_FAKE="trap", HARNESS_H2_IMPROVER="fake",
                   HARNESS_USD_RUB="80", PYTHONIOENCODING="utf-8")
        h2 = Path(d) / "h2"
        for cmd in (["step", "--out", str(h2)], ["gate", "--out", str(h2), "--reps", "1"]):
            r = subprocess.run([sys.executable, str(ROOT / "h2" / "h2.py"), *cmd], env=env, capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                failed.append(f"h2 {cmd[0]}: {(r.stderr or r.stdout)[-300:]}")
        composed = (h2 / "trees" / "composed" / "CLAUDE.md")
        if not composed.exists() or "git checkout HEAD -- <file>" not in composed.read_text(encoding="utf-8"):
            failed.append("h2: the composed tree does not carry the proposed edit")
        if not (h2 / "decision.json").exists() or "Step" not in (h2 / "lessons.pending.md").read_text(encoding="utf-8"):
            failed.append("h2: no decision.json or no lessons")
    for f in failed:
        print("FAIL", f)
    print(f"{len(TASKS)} tasks: {'all checks OK' if not failed else str(len(failed)) + ' problems'}")
    return 1 if failed else 0


if __name__ == "__main__":
    shutil.rmtree(ROOT / "bench" / "__pycache__", ignore_errors=True)
    sys.exit(main())
