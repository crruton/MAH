#!/usr/bin/env python3
"""What MAH costs the agent: tokens in each session and latency on each tool call.

  budget.py [--repo PATH] [--runs N]

Global part (CLAUDE_CONFIG_DIR or ~/.claude):
  skills   name and description of each skill are in the context of each session.
           The body loads only when the agent uses the skill. Ours: harness/installed-skills.txt.
  rules    harness/AGENTS.md, only when you installed with --rules.
  hooks    median latency of guard.sh (PreToolUse) and collect-tool-errors.sh (PostToolUse).
Project part (--repo): MCP tool definitions from <repo>/.mcp.json (extras), measured with
a real tools/list call when the mcp package is installed.
Tokens: tiktoken o200k_base when installed (an estimate for Claude), else characters / 4.
"""
import argparse
import json
import os
import queue
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

try:
    import tiktoken
    ENC = tiktoken.get_encoding("o200k_base")
    def tokens(text): return len(ENC.encode(text))
    METHOD = "tiktoken o200k"
except ImportError:
    def tokens(text): return round(len(text) / 4)
    METHOD = "chars/4 (pip install tiktoken for a better estimate)"

H = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
HH = Path(os.environ.get("HARNESS_HOME") or H / "harness")


def skills():
    mine = set((HH / "installed-skills.txt").read_text(encoding="utf-8").split()) if (HH / "installed-skills.txt").exists() else set()
    ours, other = [], []
    for f in sorted((H / "skills").glob("*/SKILL.md")):
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", f.read_text(encoding="utf-8"), re.S)
        head = m.group(1) if m else ""
        (ours if f.parent.name in mine else other).append((f.parent.name, tokens(head)))
    return ours, other


def list_tools(cmd, env, cwd):
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, encoding="utf-8", bufsize=1)
    except OSError:
        return []
    q = queue.Queue()
    threading.Thread(target=lambda: [q.put(line) for line in p.stdout], daemon=True).start()

    def send(m):
        p.stdin.write(json.dumps(m) + "\n")
        p.stdin.flush()

    def wait(i, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            try:
                m = json.loads(q.get(timeout=0.2))
            except (queue.Empty, ValueError):
                continue
            if m.get("id") == i:
                return m
        return {}

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "budget", "version": "1"}}})
        if not wait(1):
            return []
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        return wait(2).get("result", {}).get("tools", [])
    finally:
        p.kill()


def mcp(repo: Path):
    cfg = repo / ".mcp.json"
    if not cfg.exists():
        return []
    rows = []
    for name, s in json.loads(cfg.read_text(encoding="utf-8")).get("mcpServers", {}).items():
        env = dict(os.environ, **{k: v for k, v in s.get("env", {}).items() if v}, HARNESS_ROOT=str(repo))
        cmd = [sys.executable if s["command"] in ("python", "python3") else s["command"], *s.get("args", [])]
        tools = list_tools(cmd, env, repo)
        rows.append((name, len(tools), tokens(json.dumps(tools, ensure_ascii=False)) if tools else None))
    return rows


SAMPLES = {
    "guard.sh": {"tool_name": "Bash", "tool_input": {"command": "git status"}},
    "collect-tool-errors.sh": {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_response": {"stdout": "ok"}},
}


def hooks(runs: int, cwd: Path):
    bash = shutil.which("bash") or "bash"
    rows = []
    for name, sample in SAMPLES.items():
        h = HH / "hooks" / name
        if not h.exists():
            continue
        ms = []
        for _ in range(runs):
            t0 = time.perf_counter()
            subprocess.run([bash, str(h)], input=json.dumps(sample), cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", env=dict(os.environ, HARNESS_ERRORS="0"))
            ms.append((time.perf_counter() - t0) * 1000)
        rows.append((name, round(statistics.median(ms))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="")
    ap.add_argument("--runs", type=int, default=7)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    repo = Path(a.repo).resolve() if a.repo else None

    ours, other = skills()
    rules = tokens((HH / "AGENTS.md").read_text(encoding="utf-8")) if (HH / "AGENTS.md").exists() else 0
    m_rows = mcp(repo) if repo else []
    h_rows = hooks(a.runs, repo or Path.cwd())
    s_ours = sum(t for _, t in ours)
    m_tok = sum(t or 0 for _, _, t in m_rows)

    print(f"# MAH budget ({METHOD})\n")
    print("## Tokens that MAH adds to each session")
    print(f"  skills        {s_ours:>6}   {len(ours)} descriptions: {', '.join(n for n, _ in ours) or 'none'}")
    print(f"  rules         {rules:>6}   {'harness/AGENTS.md (--rules)' if rules else 'not installed (your CLAUDE.md stays as it is)'}")
    if m_rows:
        print(f"  mcp (extras)  {m_tok:>6}   {sum(c for _, c, _ in m_rows)} tools in {len(m_rows)} servers of {repo.name}/.mcp.json")
        for n, c, t in m_rows:
            print(f"                  {n:<20} {c} tools, {t if t is not None else '?'} tokens")
    print(f"  total         {s_ours + rules + m_tok:>6}")
    if other:
        print(f"  (not ours: {len(other)} other skills, {sum(t for _, t in other)} tokens)")
    print("\n## Latency on each tool call")
    for n, ms in h_rows:
        print(f"  {n:<26} {ms:>4} ms")
    if h_rows:
        print(f"  total                      {sum(ms for _, ms in h_rows):>4} ms")
    else:
        print("  no hooks: run bash install.sh")
    print("\nCompare with what the barriers stopped and how often they asked you: ./harness.sh errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
