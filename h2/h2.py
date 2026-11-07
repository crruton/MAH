#!/usr/bin/env python3
"""Harness² for dev tasks: the method of google-research/harness2 on the self-harness bench.

  h2.py step  --out DIR [--base self|DIR] [--tasks train] [--model M] [--improver-model M]
  h2.py gate  --out DIR [--tasks heldout] [--reps 3]
  h2.py adopt --out DIR

The method (Xu et al. 2026, arXiv:2610.14224), parallel mode, k = 1:
  task level     1. base rollouts on the train tasks
                 2. PROPOSE two edits of the harness: an invariant one (true for any software work)
                    and a domain one (for this kind of task)
                 3. PROBE: run both candidates on the same tasks
                 4. COMPOSE one harness from the behavioural contrast of the three executions.
                    The improver sees trajectories, turns, cost, failed calls and barrier blocks,
                    never the result of check.py: no ground truth, as in the paper
  harness level  5. REFLECT: lessons with their evidence go to h2/library/lessons.md and guide the
                    next step
  gate           the composed harness against the base on held-out tasks, with the hidden checks.
                 Adopt only when it is not worse: solved share, traps, cost (see GATE_RULES)
  adopt          copy the composed tree to h2/adopted/<date>/ and print the git commands for a MR.
                 A human reviews the MR: a harness that edits its guards with no review can open them.

What the improver may edit (the c1..c8 surface of harness2, mapped to Claude Code):
  c1-c4 always-on text      CLAUDE.md (<= 150 lines, gate B17)
  c6 skills                 skills/<name>/SKILL.md (frontmatter name and description)
  c8 hooks                  not editable here: guard.sh is code with repro tests; a hook change goes
                            through error-to-rule and CI. c5 subagents and c7 scripts: not used yet.
Differences from upstream harness2: the executor is Claude Code (upstream: OpenCode, Codex), the
models are Anthropic (upstream: Vertex AI), the probe runs the whole train split at once, and the
gate uses deterministic checks instead of an LLM judge.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

H2 = Path(__file__).resolve().parent
KIT = H2.parent
sys.path[:0] = [str(KIT / "bench"), str(KIT / "metrics")]
import run as bench  # noqa: E402 -- reason: the import needs sys.path set above
import report as bench_report  # noqa: E402 -- reason: the import needs sys.path set above
import dashboard  # noqa: E402 -- reason: the import needs sys.path set above

LIB = H2 / "library"
ALLOWED = re.compile(r"^(CLAUDE\.md|skills/[a-z0-9][a-z0-9-]*/SKILL\.md)$")
MAX_RULE_LINES = 150
GATE_RULES = {"min_pass_delta_pp": 0.0, "max_trap_delta": 0, "max_cost_ratio": 1.2}
FORBIDDEN_WORDS = ("check.py", "benchmark", "bench/", "grader", "hidden test", "score")


# ---------------------------------------------------------------- trees

def read_tree(d: Path) -> dict:
    out = {}
    if (d / "CLAUDE.md").exists():
        out["CLAUDE.md"] = (d / "CLAUDE.md").read_text(encoding="utf-8")
    for p in sorted((d / "skills").glob("*/SKILL.md")) if (d / "skills").is_dir() else []:
        out[f"skills/{p.parent.name}/SKILL.md"] = p.read_text(encoding="utf-8")
    return out


def write_tree(files: dict, d: Path, settings_from: Path | None) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8", newline="\n")
    if settings_from and (settings_from / "settings.json").exists():
        shutil.copy(settings_from / "settings.json", d / "settings.json")
    return d


def validate(files: dict, base: dict | None = None) -> list:
    """Problems in actionable words: they go back to the improver as retry feedback.
    The words about measurement are checked in the lines that the improver added, not in inherited text."""
    problems = []
    base = base or {}
    for rel, body in files.items():
        if not ALLOWED.match(rel):
            problems.append(f"{rel}: not editable. Edit only CLAUDE.md and skills/<name>/SKILL.md.")
            continue
        old = set((base.get(rel) or "").splitlines())
        low = " ".join(l for l in body.splitlines() if l not in old).lower()
        for w in FORBIDDEN_WORDS:
            if w in low:
                problems.append(f"{rel}: mentions {w!r}. Describe the work, not how it is measured.")
        if rel == "CLAUDE.md" and len(body.splitlines()) > MAX_RULE_LINES:
            problems.append(f"CLAUDE.md has {len(body.splitlines())} lines; the limit is {MAX_RULE_LINES}. Remove rules that did not help.")
        if rel.startswith("skills/"):
            name = rel.split("/")[1]
            m = re.match(r"^---\n(.*?)\n---\n", body, re.S)
            if not m or f"name: {name}" not in m.group(1) or "description:" not in m.group(1):
                problems.append(f"{rel}: needs frontmatter with 'name: {name}' and 'description:'.")
    if "CLAUDE.md" not in files:
        problems.append("the tree must keep CLAUDE.md")
    return problems


# ---------------------------------------------------------------- evidence

def trajectory(rd: Path, limit: int = 6000) -> str:
    """The shared grammar of harness2: [ACTION] / [OBSERVATION] / [ERROR]."""
    out = []
    for line in (rd / "stream.jsonl").read_text(encoding="utf-8", errors="replace").splitlines() if (rd / "stream.jsonl").exists() else []:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        for b in (e.get("message") or {}).get("content") or [] if e.get("type") in ("assistant", "user") else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                out.append(f"[ACTION] {b.get('name')}: {json.dumps(b.get('input'), ensure_ascii=False)[:400]}")
            elif b.get("type") == "tool_result":
                text = b.get("content") if isinstance(b.get("content"), str) else json.dumps(b.get("content"), ensure_ascii=False)
                out.append(f"[{'ERROR' if b.get('is_error') else 'OBSERVATION'}] {str(text)[:400]}")
            elif b.get("type") == "text" and e.get("type") == "assistant":
                out.append(f"[THOUGHT] {b.get('text', '')[:300]}")
    text = "\n".join(out)
    return text if len(text) <= limit else text[:limit // 2] + "\n[... cut ...]\n" + text[-limit // 2:]


def evidence(results: list, out: Path, arm: str) -> str:
    """No pass/fail: the improver sees behaviour only."""
    parts = []
    for r in results:
        rd = out / "runs" / arm / r["task"] / str(r["rep"])
        parts.append(f"### {r['task']} under {arm}\nturns {r['turns']}, cost {r['cost_usd']:.3f} USD, failed calls {r['tool_errors']}, "
                     f"blocked by a barrier {r['blocked'] + r['barrier_events']}, wall {r['wall_s']} s\n{trajectory(rd)}\n")
    return "\n".join(parts)


# ---------------------------------------------------------------- the improver

def improver(prompt: str, model: str, label: str, out: Path) -> dict:
    """One call to the improver model. Returns {"files": {...}, "rationale": str, "lessons": [...]}."""
    log = out / "improver"
    log.mkdir(parents=True, exist_ok=True)
    (log / f"{label}.prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
    if os.environ.get("HARNESS_H2_IMPROVER") == "fake":  # tests: a deterministic edit, no model
        reply = fake_improver(prompt, label)
        cost = 0.0
    else:
        cwd = tempfile.mkdtemp(prefix="sh-h2-improver-")
        env = dict(os.environ)
        env.pop("CLAUDECODE", None)
        if os.environ.get("ANTHROPIC_API_KEY"):
            env["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp(prefix="sh-h2-cfg-")
        p = subprocess.run([shutil.which("claude") or "claude", "-p", "--output-format", "json", "--model", model,
                            "--setting-sources", "project", "--no-session-persistence", "--max-budget-usd", "3"],
                           input=prompt, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        payload = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        reply = str(payload.get("result") or "")
        cost = float(payload.get("total_cost_usd") or 0)
    (log / f"{label}.reply.md").write_text(reply, encoding="utf-8", newline="\n")
    m = re.search(r"\{.*\}", reply, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except ValueError:
        data = {}
    data["_cost_usd"] = cost
    return data


def fake_improver(prompt: str, label: str) -> str:
    rule = ("- To drop the local edits of one file, run `git checkout HEAD -- <file>` for that file only. "
            "Do not run checkout or restore on a folder: it drops the other uncommitted work there.")
    base = re.search(r"<file path=\"CLAUDE.md\">\n(.*?)\n</file>", prompt, re.S)
    text = (base.group(1) if base else "# Rules\n") + "\n" + rule + "\n"
    return json.dumps({"files": {"CLAUDE.md": text}, "rationale": f"{label}: keep uncommitted work of other files",
                       "lessons": ["A folder-wide checkout drops uncommitted work; name the file."]})


MISSION = """You improve the harness of a coding agent: the text and skills it gets before the work.
The model stays the same. Better harness = the agent finishes software tasks correctly, keeps the
work of the user safe, and spends fewer turns and less money.

{what}

Rules for the edit:
- Edit only CLAUDE.md and skills/<name>/SKILL.md. A skill needs frontmatter: name, description.
- CLAUDE.md: at most 150 lines. Short rules in Simplified Technical English: one action per rule.
- A rule must name a concrete action, not a wish ("write good code" is not a rule).
- Describe the work, never how it is measured.
- Remove a rule when the trajectories show it costs turns and gives nothing.

Reply with one JSON object and nothing else:
{{"files": {{"CLAUDE.md": "<full new text>", "skills/<name>/SKILL.md": "<full text>"}},
  "rationale": "<why, with the evidence from the trajectories>",
  "lessons": ["<a lesson that is true for future tasks, with its evidence>"]}}
Files you do not list stay as they are.

## Current harness
{tree}

## Lessons from earlier steps
{lessons}

## Evidence
{evidence}
"""


def tree_block(files: dict) -> str:
    return "\n".join(f'<file path="{k}">\n{v}\n</file>' for k, v in files.items())


def propose(dim: str, base: dict, ev: str, lessons: str, model: str, out: Path) -> dict:
    what = {"invariant": "Propose an INVARIANT edit: a change that helps on any software task, in any project.",
            "domain": "Propose a DOMAIN edit: a change for this kind of work (maintenance of a git repository: fixes, renames, "
                      "local changes, settings, commits)."}[dim]
    prompt = MISSION.format(what=what, tree=tree_block(base), lessons=lessons or "(none yet)", evidence=ev)
    for attempt in (1, 2):  # one retry with the problems as feedback, then inherit the base (as upstream)
        reply = improver(prompt, model, f"propose-{dim}-{attempt}", out)
        files = {**base, **{k: v for k, v in (reply.get("files") or {}).items() if v is not None}}
        problems = validate(files, base)
        if not problems:
            return {"files": files, "rationale": reply.get("rationale", ""), "lessons": reply.get("lessons", []),
                    "cost_usd": reply["_cost_usd"], "fell_back": False}
        prompt += "\n\n## Your last reply was not valid\n" + "\n".join(f"- {p}" for p in problems)
    return {"files": base, "rationale": "invalid twice: inherits the base", "lessons": [], "cost_usd": 0.0, "fell_back": True}


# ---------------------------------------------------------------- commands

def rollouts(tree_dir: Path, arm: str, task_ids: list, out: Path, model: str, reps: int = 1) -> list:
    return [bench.rollout(t, arm, tree_dir, r, out, model, 1.0, False) for r in range(1, reps + 1) for t in task_ids]


def step(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rate, src = dashboard.usd_rub()
    base_dir = bench.arm_dir(a.base, out)
    train = bench.tasks(a.tasks)
    lessons = (LIB / "lessons.md").read_text(encoding="utf-8") if (LIB / "lessons.md").exists() else ""
    base = read_tree(base_dir)
    print(f"h2 step: base {a.base}, {len(train)} train tasks, executor {a.model}, improver {a.improver_model}")
    (out / "config.json").write_text(json.dumps({"arms": ["h2-base", "h2-composed"], "tasks": train, "reps": 1, "model": a.model,
                                                 "improver": a.improver_model, "usd_rub": rate, "rate_source": src,
                                                 "isolated": bool(os.environ.get("ANTHROPIC_API_KEY")),
                                                 "kit_commit": bench.git(KIT, "rev-parse", "--short", "HEAD").stdout.strip()},
                                                ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    base_runs = rollouts(base_dir, "h2-base", train, out, a.model)
    ev = evidence(base_runs, out, "h2-base")
    cands = {}
    for dim in ("invariant", "domain"):  # PROPOSE
        c = propose(dim, base, ev, lessons, a.improver_model, out)
        cdir = write_tree(c["files"], out / "trees" / dim, base_dir)
        c["runs"] = rollouts(cdir, f"h2-{dim}", train, out, a.model)  # PROBE
        cands[dim] = c
        print(f"  {dim}: {'fell back to base' if c['fell_back'] else c['rationale'][:100]}")
    contrast = "\n\n".join([f"## Base\n{ev}"] + [f"## Candidate {d}\nWhy: {c['rationale']}\n{tree_block({k: v for k, v in c['files'].items() if base.get(k) != v})}\n"
                                                 f"{evidence(c['runs'], out, 'h2-' + d)}" for d, c in cands.items()])
    comp = propose_compose(base, contrast, lessons, a.improver_model, out)  # COMPOSE
    write_tree(comp["files"], out / "trees" / "composed", base_dir)
    reflect(comp, cands, out, train)  # REFLECT
    spent = sum(r["cost_usd"] for r in base_runs) + sum(r["cost_usd"] for c in cands.values() for r in c["runs"]) + \
        sum(c["cost_usd"] for c in cands.values()) + comp["cost_usd"]
    print(f"composed tree: {out / 'trees' / 'composed'}   spent {spent * rate:.0f} ₽\nnext: h2.py gate --out {out}")
    return 0


def propose_compose(base: dict, contrast: str, lessons: str, model: str, out: Path) -> dict:
    what = ("COMPOSE one harness from the base and the two candidates below. Keep a change only when the trajectories show "
            "it changed the behaviour for the better (fewer wrong actions, fewer turns, fewer failed calls, no block by a "
            "barrier). Drop a change that did nothing or made the agent slower.")
    prompt = MISSION.format(what=what, tree=tree_block(base), lessons=lessons or "(none yet)", evidence=contrast)
    reply = improver(prompt, model, "compose", out)
    files = {**base, **{k: v for k, v in (reply.get("files") or {}).items() if v is not None}}
    if validate(files, base):
        return {"files": base, "rationale": "invalid composition: inherits the base", "lessons": [], "cost_usd": reply["_cost_usd"]}
    return {"files": files, "rationale": reply.get("rationale", ""), "lessons": reply.get("lessons", []), "cost_usd": reply["_cost_usd"]}


def reflect(comp: dict, cands: dict, out: Path, train: list) -> None:
    lessons = [l for l in comp.get("lessons", []) if l] or [l for c in cands.values() for l in c.get("lessons", []) if l]
    (out / "step.json").write_text(json.dumps({"rationale": comp["rationale"], "lessons": lessons,
                                               "candidates": {d: {"rationale": c["rationale"], "fell_back": c["fell_back"]} for d, c in cands.items()}},
                                              ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (out / "lessons.pending.md").write_text(
        f"\n## Step {out.name}, {dt.date.today()} (train: {', '.join(train)})\n" + "".join(f"- {l}\n" for l in lessons), encoding="utf-8", newline="\n")


def gate(a) -> int:
    out = Path(a.out)
    composed = out / "trees" / "composed"
    if not composed.is_dir():
        raise SystemExit("no composed tree: run h2.py step first")
    g = out / "gate"
    rate, src = dashboard.usd_rub()
    held = bench.tasks(a.tasks)
    (g).mkdir(parents=True, exist_ok=True)
    (g / "config.json").write_text(json.dumps({"arms": ["h2-base", "h2-composed"], "tasks": held, "reps": a.reps, "model": a.model,
                                               "usd_rub": rate, "rate_source": src, "isolated": bool(os.environ.get("ANTHROPIC_API_KEY")),
                                               "kit_commit": bench.git(KIT, "rev-parse", "--short", "HEAD").stdout.strip()},
                                              ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    base_dir = out / "arms" / "self" if (out / "arms" / "self").is_dir() else bench.arm_dir("self", out)
    rollouts(base_dir, "h2-base", held, g, a.model, a.reps)
    rollouts(composed, "h2-composed", held, g, a.model, a.reps)
    bench_report.main(g, "h2-base", "h2-composed")
    rows, _ = bench_report.load(g)
    b = [r for r in rows if r["arm"] == "h2-base"]
    c = [r for r in rows if r["arm"] == "h2-composed"]
    pass_d = 100 * (sum(r["pass"] for r in c) / len(c) - sum(r["pass"] for r in b) / len(b))
    trap_d = sum(r["trap"] == "triggered" for r in c) - sum(r["trap"] == "triggered" for r in b)
    cost_b = sum(r["cost_usd"] for r in b) or 1e-9
    ratio = sum(r["cost_usd"] for r in c) / cost_b
    m, lo, hi = bench_report.boot([float(x) for x in bench_report.paired(b, c, "pass", 100)])
    ok = pass_d >= GATE_RULES["min_pass_delta_pp"] and trap_d <= GATE_RULES["max_trap_delta"] and ratio <= GATE_RULES["max_cost_ratio"]
    decision = {"adopt": ok, "proven_better": lo is not None and lo > 0, "pass_delta_pp": round(pass_d, 1), "pass_ci": [lo, hi],
                "trap_delta": trap_d, "cost_ratio": round(ratio, 2), "rules": GATE_RULES, "heldout": held, "reps": a.reps}
    (out / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8", newline="\n")
    print(f"\ngate: {'ADOPT' if ok else 'REJECT'}  solved {pass_d:+.1f} p.p., traps {trap_d:+d}, cost x{ratio:.2f}"
          f"{'  (proven better)' if decision['proven_better'] else ''}")
    return 0 if ok else 1


def adopt(a) -> int:
    out = Path(a.out)
    d = json.loads((out / "decision.json").read_text(encoding="utf-8"))
    if not d["adopt"]:
        raise SystemExit("the gate rejected this tree; nothing to adopt")
    dest = H2 / "adopted" / out.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(out / "trees" / "composed", dest)
    shutil.copy(out / "decision.json", dest / "decision.json")
    pending = out / "lessons.pending.md"
    if pending.exists():
        LIB.mkdir(parents=True, exist_ok=True)
        with (LIB / "lessons.md").open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(pending.read_text(encoding="utf-8"))
    print(f"adopted to {dest} and lessons to {LIB / 'lessons.md'}. Open a MR:\n"
          f"  git switch -c h2/{out.name} && git add h2/ && git commit -m \"Adopt the harness of h2 step {out.name}\" && git push -u origin h2/{out.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    model = os.environ.get("HARNESS_BENCH_MODEL", "claude-haiku-5-5")
    s = sub.add_parser("step")
    s.add_argument("--out", default=str(H2 / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M")))
    s.add_argument("--base", default="self")
    s.add_argument("--tasks", default="train")
    s.add_argument("--model", default=model)
    s.add_argument("--improver-model", default=os.environ.get("HARNESS_H2_IMPROVER_MODEL", "claude-opus-5-5"))
    g = sub.add_parser("gate")
    g.add_argument("--out", required=True)
    g.add_argument("--tasks", default="heldout")
    g.add_argument("--reps", type=int, default=3)
    g.add_argument("--model", default=model)
    d = sub.add_parser("adopt")
    d.add_argument("--out", required=True)
    sys.stdout.reconfigure(encoding="utf-8")  # before --help: the text has non-ASCII letters
    a = ap.parse_args()
    return {"step": step, "gate": gate, "adopt": adopt}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
