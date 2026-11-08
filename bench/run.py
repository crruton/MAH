#!/usr/bin/env python3
"""Bench: does a harness make the agent better on real dev tasks? A/B with repeats and a hidden check.

  run.py run    --arms none,self --tasks all --reps 3 [--model M] [--jobs 4] [--out DIR]
  run.py report --out DIR [--base none] [--arm self]
  run.py arm    self DIR      write the "self" arm (the rules, skills and hooks of this kit) to DIR

One run = one task, one arm (a harness tree), one repeat:
  1. a fresh git repository from bench/tasks/<task>/repo, first commit, then setup.py (dirty state, hooks);
  2. the arm is installed into the repository only: CLAUDE.md, .claude/skills, .claude/settings.json;
  3. `claude -p` runs the task with --setting-sources project (your user hooks and skills stay out);
  4. bench/tasks/<task>/check.py checks the result. The agent never sees check.py.
Each run writes stream.jsonl, result.json and check.json to <out>/runs/<arm>/<task>/<rep>/.

A harness tree (an arm) is a folder:  CLAUDE.md, skills/<name>/SKILL.md, settings.json
(settings.json may use ${KIT} for the path of this kit). "none" is the empty tree.

Executor: the model id picks it, as in harness2. "provider/model" (deepseek/..., openrouter/..., groq/...,
ollama/...) runs OpenCode: any provider, no vendor lock. A bare id (claude-...) runs Claude Code.
HARNESS_BENCH_EXECUTOR=fake runs the reference solution or the trap with no model (tests).
The same arm installs as CLAUDE.md + .claude/ for Claude Code, and as AGENTS.md + .opencode/ for OpenCode;
the guard is the same guard.sh: a hook in Claude Code, hooks/opencode-guard.js in OpenCode.

Isolation: with ANTHROPIC_API_KEY set, each run gets an empty CLAUDE_CONFIG_DIR: nothing of your
machine reaches the agent, and the result is reproducible on another machine. Without the key the
runs use your Claude Code login; then your user CLAUDE.md is loaded in every arm (the same text in
each arm, so the difference between arms stays fair). The report says which mode ran.

Budget: --budget-rub (default 1500). The run stops before a new rollout when the spend reaches it.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
KIT = BENCH.parent
TASKS = BENCH / "tasks"
sys.path.insert(0, str(KIT / "metrics"))
import dashboard  # noqa: E402 -- reason: the import needs sys.path set above

TOOLS = "Bash,Read,Edit,Write,Glob,Grep"
_lock = threading.Lock()


def posix(p) -> str:
    return str(p).replace("\\", "/")


def executor(model: str) -> str:
    if os.environ.get("HARNESS_BENCH_EXECUTOR") == "fake":
        return "fake"
    return "opencode" if "/" in model else "claude"


def tasks(selector: str):
    every = sorted(p.name for p in TASKS.iterdir() if (p / "task.md").exists())
    if selector in ("all", ""):
        return every
    if selector in ("train", "heldout"):
        return [t for t in every if json.loads((TASKS / t / "meta.json").read_text(encoding="utf-8"))["split"] == selector]
    want = [w.strip().rstrip("/\\") for w in selector.split(",")]  # `ls -F` adds "/": a list from it ran 0 tasks once
    unknown = [w for w in want if w and w not in every]
    if unknown:
        raise SystemExit(f"unknown tasks: {', '.join(unknown)}")
    return [t for t in every if t in want]


# ---------------------------------------------------------------- arms

def write_self_arm(dest: Path, absolute: bool = False) -> Path:
    """absolute=True writes the path of THIS kit into the hooks: CI builds the arm of the base branch from its own checkout."""
    """The kit as a harness tree: global rules, 5 process skills, guard and collector hooks."""
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(KIT / "templates" / "AGENTS.global.md", dest / "CLAUDE.md")
    for s in (KIT / "skills").iterdir():
        if (s / "SKILL.md").exists():
            (dest / "skills" / s.name).mkdir(parents=True, exist_ok=True)
            shutil.copy(s / "SKILL.md", dest / "skills" / s.name / "SKILL.md")
    settings = {"hooks": {
        "PreToolUse": [{"matcher": "Bash|Read|Edit|MultiEdit|Write|NotebookEdit",
                        "hooks": [{"type": "command", "command": 'bash "${KIT}/hooks/guard.sh"', "timeout": 10}]}],
        "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": 'bash "${KIT}/hooks/collect-tool-errors.sh"', "timeout": 10}]}],
    }}
    body = json.dumps(settings, indent=2) + "\n"
    if absolute:
        body = body.replace("${KIT}", posix(KIT))
    (dest / "settings.json").write_text(body, encoding="utf-8", newline="\n")
    return dest


def write_lean_arm(dest: Path) -> Path:
    """The short layer: templates/AGENTS.lean.md and the same hooks, no skills."""
    write_self_arm(dest)
    shutil.copy(KIT / "templates" / "AGENTS.lean.md", dest / "CLAUDE.md")
    shutil.rmtree(dest / "skills", ignore_errors=True)
    return dest


def arm_dir(name: str, out: Path) -> Path:
    if name == "none":
        d = out / "arms" / "none"
        d.mkdir(parents=True, exist_ok=True)
        return d
    if name == "self":
        return write_self_arm(out / "arms" / "self")
    if name == "lean":
        return write_lean_arm(out / "arms" / "lean")
    p = Path(name)
    if not p.is_dir():
        raise SystemExit(f"arm {name!r}: not 'none', not 'self', not a folder")
    return p


def install_arm(arm: Path, ws: Path, ex: str = "claude") -> None:
    exclude = ws / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if ex == "opencode":  # the same tree in OpenCode places
        if (arm / "CLAUDE.md").exists():
            shutil.copy(arm / "CLAUDE.md", ws / "AGENTS.md")
            lines.append("/AGENTS.md")
        if (arm / "skills").is_dir():
            shutil.copytree(arm / "skills", ws / ".opencode" / "skills", dirs_exist_ok=True)
        if (arm / "settings.json").exists() and "guard.sh" in (arm / "settings.json").read_text(encoding="utf-8"):
            (ws / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
            body = (KIT / "hooks" / "opencode-guard.js").read_text(encoding="utf-8").replace("${KIT}", posix(KIT))
            (ws / ".opencode" / "plugins" / "harness-guard.js").write_text(body, encoding="utf-8", newline="\n")
        if (ws / ".opencode").exists():
            lines.append("/.opencode/")
        with exclude.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        return
    if (arm / "CLAUDE.md").exists():
        shutil.copy(arm / "CLAUDE.md", ws / "CLAUDE.md")
        lines.append("/CLAUDE.md")
    if (arm / "skills").is_dir():
        shutil.copytree(arm / "skills", ws / ".claude" / "skills", dirs_exist_ok=True)
    if (arm / "settings.json").exists():
        (ws / ".claude").mkdir(exist_ok=True)
        body = (arm / "settings.json").read_text(encoding="utf-8").replace("${KIT}", posix(KIT))
        (ws / ".claude" / "settings.json").write_text(body, encoding="utf-8", newline="\n")
    if (ws / ".claude").exists():
        lines.append("/.claude/")
    with exclude.open("a", encoding="utf-8", newline="\n") as fh:  # the harness is not part of the task
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- one rollout

def remove_tree(path: Path) -> None:
    """Git keeps its objects read-only; on Windows rmtree fails on them, and the workspaces piled up (1300 of them)."""
    import stat

    def again(func, p, _):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=again) if sys.version_info < (3, 12) else shutil.rmtree(path, onexc=again)


def git(ws: Path, *args):
    return subprocess.run(["git", *args], cwd=ws, capture_output=True, text=True, encoding="utf-8", errors="replace")


def prepare(task: str, ws: Path) -> None:
    shutil.copytree(TASKS / task / "repo", ws)
    git(ws, "init", "-q", "-b", "main")
    git(ws, "config", "user.email", "bench@example.com")
    git(ws, "config", "user.name", "bench")
    git(ws, "config", "core.autocrlf", "false")
    git(ws, "add", "-A")
    git(ws, "commit", "-q", "-m", "Start the task")
    if (TASKS / task / "setup.py").exists():
        subprocess.run([sys.executable, str(TASKS / task / "setup.py")], cwd=ws, check=True, capture_output=True)


def parse_opencode(lines: list, out: dict) -> dict:
    """OpenCode --format json: tool parts with a state, step-finish parts with cost and tokens (as harness2 reads it)."""
    for e in lines:
        p = e.get("part") if isinstance(e.get("part"), dict) else {}
        t = p.get("type") or e.get("type")
        if t == "tool":
            out["calls"] += 1
            st = p.get("state") if isinstance(p.get("state"), dict) else {}
            if st.get("status") == "error":
                msg = str(st.get("error", ""))
                out["blocked" if "Blocked by" in msg else "tool_errors"] += 1
        elif t in ("step-finish", "step_finish"):
            out["turns"] += 1
            out["cost_usd"] += float(p.get("cost") or 0)
            tok = p.get("tokens") or {}
            out["tokens_in"] += int(tok.get("input") or 0)
            out["tokens_out"] += int(tok.get("output") or 0) + int(tok.get("reasoning") or 0)
            out["tokens_cache_read"] += int((tok.get("cache") or {}).get("read") or 0)
        elif e.get("type") == "error":
            out["result_error"] = True
            out["subtype"] = str((e.get("error") or {}).get("message", ""))[:120]
    return out


def parse_stream(path: Path) -> dict:
    out = {"calls": 0, "tool_errors": 0, "blocked": 0, "denied": 0, "cost_usd": 0.0, "turns": 0, "duration_ms": 0,
           "tokens_in": 0, "tokens_out": 0, "tokens_cache_read": 0, "result_error": False, "subtype": ""}
    if not path.exists():
        return out
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    if any("part" in e for e in events if isinstance(e, dict)):
        return parse_opencode(events, out)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            out["calls"] += sum(1 for b in (e.get("message") or {}).get("content") or [] if isinstance(b, dict) and b.get("type") == "tool_use")
        elif e.get("type") == "user":
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                    text = json.dumps(b.get("content"), ensure_ascii=False)
                    if "Blocked by" in text:
                        out["blocked"] += 1
                    elif "permission" in text.lower() or "denied" in text.lower():
                        out["denied"] += 1
                    else:
                        out["tool_errors"] += 1
        elif e.get("type") == "result":
            u = e.get("usage") or {}
            out.update(cost_usd=float(e.get("total_cost_usd") or 0), turns=int(e.get("num_turns") or 0),
                       duration_ms=int(e.get("duration_ms") or 0), result_error=bool(e.get("is_error")), subtype=e.get("subtype", ""),
                       tokens_in=int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0),
                       tokens_out=int(u.get("output_tokens") or 0), tokens_cache_read=int(u.get("cache_read_input_tokens") or 0))
    return out


def rollout(task: str, arm_name: str, arm: Path, rep: int, out: Path, model: str, budget_usd_per_run: float, keep: bool) -> dict:
    # absolute: check.py runs parts of itself from the workspace, a relative --out pointed there (q07 failed 10 of 10)
    rd = (Path(out) / "runs" / Path(arm_name).name / task / str(rep)).resolve()
    if (rd / "result.json").exists():  # resume
        return {**json.loads((rd / "result.json").read_text(encoding="utf-8")), "_resumed": True}
    rd.mkdir(parents=True, exist_ok=True)
    ws = Path(tempfile.mkdtemp(prefix=f"sh-bench-{task}-")) / "w"
    prepare(task, ws)
    ex = executor(model)
    install_arm(arm, ws, ex)
    meta = json.loads((TASKS / task / "meta.json").read_text(encoding="utf-8"))
    prompt = (TASKS / task / "task.md").read_text(encoding="utf-8").strip() + "\n\nWork in the current directory. Do not ask questions: decide and finish the task. When done, reply DONE."
    env = dict(os.environ, HARNESS_HOME=str(rd / "harness"), HARNESS_ERRORS="1")
    env.pop("CLAUDECODE", None)  # a nested agent is a new session, not a part of this one
    isolated = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if isolated:
        env["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp(prefix="sh-bench-cfg-")
    cmd = [shutil.which("claude") or "claude", "-p", "--output-format", "stream-json", "--verbose", "--model", model,
           "--setting-sources", "project", "--permission-mode", "acceptEdits", "--allowedTools", TOOLS,
           "--max-budget-usd", str(budget_usd_per_run), "--no-session-persistence"]
    if ex == "opencode":  # any provider; the user config stays out, the provider login (auth.json) stays in
        cfg = tempfile.mkdtemp(prefix="sh-bench-oc-")
        env.update(XDG_CONFIG_HOME=cfg, HARNESS_BASH=posix(shutil.which("bash") or "bash"),
                   OPENCODE_PERMISSION=json.dumps({"external_directory": {"*": "deny", posix(ws): "allow", posix(ws) + "/**": "allow"}}))
        cmd = [shutil.which("opencode") or "opencode", "run", "--model", model, "--format", "json", "--auto", prompt]
        isolated = True
    if ex == "fake":  # no model: the reference solution or the trap
        cmd = [sys.executable, str(BENCH / "fake_agent.py")]
        env["HARNESS_BENCH_TASK_DIR"] = str(TASKS / task)
    t0 = time.time()
    with (rd / "stream.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        try:
            p = subprocess.run(cmd, cwd=ws, env=env, input=prompt, stdout=fh, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", errors="replace", timeout=int(meta.get("timeout", 600)))
            rc, err = p.returncode, (p.stderr or "")[-400:]
        except subprocess.TimeoutExpired:
            rc, err = -1, "timeout"
    wall = time.time() - t0
    chk = subprocess.run([sys.executable, str(TASKS / task / "check.py"), str(ws), str(rd)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        check = json.loads(chk.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        check = {"pass": False, "trap": "n/a", "details": {"check_error": (chk.stderr or chk.stdout)[-300:]}}
    (rd / "check.json").write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    events = [json.loads(l) for f in (rd / "harness" / "errors").glob("*.jsonl") for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if (rd / "harness" / "errors").is_dir() else []
    res = {"task": task, "arm": Path(arm_name).name, "rep": rep, "split": meta["split"], "kind": meta["kind"], "model": model,
           "isolated": isolated, "executor": ex, "rc": rc, "stderr": err, "wall_s": round(wall, 1), "pass": bool(check.get("pass")),
           "trap": check.get("trap", "n/a"), "check": check.get("details", {}),
           "danger": check.get("danger", [meta["danger"]] if check.get("trap") == "triggered" and meta.get("danger") else []), **parse_stream(rd / "stream.jsonl"),
           "barrier_events": len(events), "barrier_asked": sum(1 for e in events if e.get("outcome") == "asked"),
           "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    (rd / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    if not keep:
        remove_tree(ws.parent)
    return res


# ---------------------------------------------------------------- the run

def run(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rate, src = dashboard.usd_rub()
    if not rate:
        raise SystemExit("no USD->RUB rate: set HARNESS_USD_RUB")
    budget_usd = a.budget_rub / rate
    arms = {n: arm_dir(n, out) for n in a.arms.split(",")}
    todo = [(t, n, r) for r in range(1, a.reps + 1) for t in tasks(a.tasks) for n in arms]
    spent = [sum(json.loads(p.read_text(encoding="utf-8")).get("cost_usd", 0) for p in out.glob("runs/*/*/*/result.json"))]
    (out / "config.json").write_text(json.dumps({"arms": list(arms), "tasks": tasks(a.tasks), "reps": a.reps, "model": a.model,
                                                 "budget_rub": a.budget_rub, "usd_rub": rate, "rate_source": src,
                                                 "isolated": bool(os.environ.get("ANTHROPIC_API_KEY")) or executor(a.model) == "opencode",
                                                 "executor": executor(a.model),
                                                 "claude": subprocess.run([shutil.which("claude") or "claude", "--version"], capture_output=True, text=True, encoding="utf-8").stdout.strip(),
                                                 "kit_commit": git(KIT, "rev-parse", "--short", "HEAD").stdout.strip()},
                                                ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"bench: {len(todo)} rollouts, model {a.model}, budget {a.budget_rub} ₽ ({src}), out {out}")

    def one(item):
        t, n, r = item
        with _lock:
            if spent[0] >= budget_usd:
                return None
        res = rollout(t, n, arms[n], r, out, a.model, a.run_budget_usd, a.keep)
        with _lock:
            spent[0] += 0 if res.get("_resumed") else res.get("cost_usd", 0)  # resumed runs are in the start sum
            print(f"  {res['arm']:<10} {t:<24} #{r}  {'PASS' if res['pass'] else 'fail'}  trap={res['trap']:<9} "
                  f"{res['cost_usd'] * rate:7.1f} ₽  {res['wall_s']:6.0f} s  spent {spent[0] * rate:7.0f} ₽", flush=True)
        return res

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = [r for r in ex.map(one, todo) if r]
    with (out / "results.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for p in sorted(out.glob("runs/*/*/*/result.json")):
            fh.write(p.read_text(encoding="utf-8").replace("\n", " ") + "\n")
    skipped = len(todo) - len(results)
    print(f"done: {len(results)} rollouts, {spent[0] * rate:.0f} ₽" + (f", {skipped} skipped by the budget" if skipped else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arms", default="none,self")
    r.add_argument("--tasks", default="all")
    r.add_argument("--reps", type=int, default=3)
    r.add_argument("--model", default=os.environ.get("HARNESS_BENCH_MODEL", "claude-haiku-5-5"))
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--budget-rub", type=float, default=float(os.environ.get("HARNESS_BENCH_BUDGET_RUB", "1500")))
    r.add_argument("--run-budget-usd", type=float, default=1.0)
    r.add_argument("--out", default=str(BENCH / "results" / dt.date.today().isoformat()))
    r.add_argument("--keep", action="store_true", help="keep the workspaces")
    rp = sub.add_parser("report")
    rp.add_argument("--out", required=True)
    rp.add_argument("--base", default="none")
    rp.add_argument("--arm", default="self")
    rp.add_argument("--fail-if-worse", action="store_true", help="exit 1 when the arm is proven worse in solved share, or hits more traps")
    w = sub.add_parser("arm")
    w.add_argument("name", choices=["self"])
    w.add_argument("dest")
    w.add_argument("--absolute", action="store_true", help="hooks point to this kit, not to the kit that runs the bench")
    sys.stdout.reconfigure(encoding="utf-8")  # before --help: the text has non-ASCII letters
    a = ap.parse_args()
    if a.cmd == "run":
        return run(a)
    if a.cmd == "arm":
        print(write_self_arm(Path(a.dest), a.absolute))
        return 0
    import report
    return report.main(Path(a.out), a.base, a.arm, a.fail_if_worse)


if __name__ == "__main__":
    sys.exit(main())
