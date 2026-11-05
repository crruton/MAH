#!/usr/bin/env python3
"""Cost of the harness for the agent: tokens in each session and hook latency on each tool call.

  budget.py [--repo PATH] [--runs N]

What the agent pays:
  rules      CLAUDE.md, AGENTS.md and their @imports: read at the start of each session.
  skills     name and description of each skill: in the context of each session.
             The body loads only when the agent uses the skill.
  mcp        tool definitions of each MCP server from .mcp.json: in the context of each session.
             Measured with a real tools/list call when the mcp package is installed.
  hooks      latency of each hook on each matching tool call (median of N runs).
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


def rules(repo: Path):
    seen, total, rows = set(), 0, []

    def add(p: Path):
        nonlocal total
        if not p.exists() or p in seen:
            return
        seen.add(p)
        text = p.read_text(encoding="utf-8")
        t = tokens(text)
        total += t
        rows.append((str(p.relative_to(repo)) if repo in p.parents or p == repo else str(p), t))
        for imp in re.findall(r"^@(\S+)", text, re.M):
            add((p.parent / imp).resolve())

    add(repo / "CLAUDE.md")
    add(repo / "AGENTS.md")
    return total, rows


def skills(repo: Path):
    rows = []
    for f in sorted((repo / ".claude" / "skills").glob("*/SKILL.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        head, body = (m.group(1), m.group(2)) if m else ("", text)
        rows.append((f.parent.name, tokens(head), tokens(body)))
    return rows


def mcp_tools(repo: Path):
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


SAMPLES = {
    "guard.sh": {"tool_name": "Bash", "tool_input": {"command": "git status"}},
    "collect-tool-errors.sh": {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_response": {"stdout": "ok"}},
}


def hooks(repo: Path, runs: int):
    bash = shutil.which("bash") or "bash"
    rows = []
    for name, sample in SAMPLES.items():
        h = repo / ".claude" / "hooks" / name
        if not h.exists():
            continue
        ms = []
        for _ in range(runs):
            t0 = time.perf_counter()
            subprocess.run([bash, str(h)], input=json.dumps(sample), cwd=repo, capture_output=True,
                           text=True, encoding="utf-8")
            ms.append((time.perf_counter() - t0) * 1000)
        rows.append((name, round(statistics.median(ms))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    sys.stdout.reconfigure(encoding="utf-8")

    r_total, r_rows = rules(repo)
    s_rows = skills(repo)
    m_rows = mcp_tools(repo)
    h_rows = hooks(repo, a.runs)
    s_head = sum(r[1] for r in s_rows)
    m_tok = sum(r[2] or 0 for r in m_rows)

    print(f"# Harness budget ({METHOD})\n")
    print("## Tokens in each session")
    print(f"  rules        {r_total:>6}   " + ", ".join(f"{n} {t}" for n, t in r_rows))
    print(f"  skills       {s_head:>6}   {len(s_rows)} descriptions (bodies {sum(r[2] for r in s_rows)} tokens load only on use)")
    if m_rows:
        failed = [n for n, c, t in m_rows if t is None]
        print(f"  mcp          {m_tok:>6}   {sum(c for _, c, _ in m_rows)} tools in {len(m_rows)} servers"
              + (f"  (not measured: {', '.join(failed)} — pip install -r .harness/mcp/requirements.txt)" if failed else ""))
        for n, c, t in m_rows:
            print(f"                 {n:<20} {c} tools, {t if t is not None else '?'} tokens")
    else:
        print("  mcp               0   no .mcp.json")
    print(f"  total        {r_total + s_head + m_tok:>6}")
    print("\n## Latency on each tool call")
    for n, ms in h_rows:
        print(f"  {n:<26} {ms:>4} ms")
    print(f"  each tool call: ~{sum(ms for _, ms in h_rows)} ms (PreToolUse guard.sh + PostToolUse collect-tool-errors.sh)")
    print("\nCompare this cost with the errors the barriers stopped: ./harness.sh errors <repo>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
