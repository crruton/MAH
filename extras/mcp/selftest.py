"""Self-test of the 10 harness MCP servers.

1. Protocol: start each server over stdio, send initialize and tools/list (raw JSON-RPC).
2. Behavior: call the tool functions of each server on a throwaway git repository.
Usage: python mcp/selftest.py   (needs: pip install -r mcp/requirements.txt)
"""
import importlib
import json
import os
import subprocess
import queue
import sys
import threading
import time
import tempfile
from pathlib import Path

SERVERS = Path(__file__).resolve().parent / "servers"
NAMES = ["test_env_broker", "safe_edit", "spec_registry", "quality_gate", "context_freshness",
         "pii_reader", "schema_store", "readonly_view", "slot_scheduler", "redteam_runner"]
fails = []


def check(name, cond, note=""):
    print(f"  {'ok ' if cond else 'FAIL'} {name}{(': ' + note) if note else ''}")
    if not cond:
        fails.append(name)


def protocol(name, env):
    """initialize -> initialized -> tools/list. Wait for each answer before the next step:
    a server can stop at end of input before it answers."""
    p = subprocess.Popen([sys.executable, str(SERVERS / f"{name}.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, encoding="utf-8", env=env, bufsize=1)
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(l) for l in p.stdout], daemon=True).start()

    def send(msg):
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()

    def answer(msg_id, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            try:
                m = json.loads(lines.get(timeout=max(0.1, end - time.time())))
            except (queue.Empty, ValueError):
                continue
            if m.get("id") == msg_id:
                return m
        return {}

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "selftest", "version": "1"}}})
        if not answer(1):
            return []
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        return [t["name"] for t in answer(2).get("result", {}).get("tools", [])]
    finally:
        p.kill()
        p.wait()


def main():
    repo = Path(tempfile.mkdtemp())
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)
    run("init", "-q", "-b", "dev")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
    (repo / "core").mkdir()
    (repo / "core" / "engine.txt").write_text("core logic", encoding="utf-8", newline="\n")
    (repo / "data").mkdir()
    (repo / "data" / "calls.txt").write_text("Call from ivan@example.com, phone +7 912 345-67-89\n", encoding="utf-8", newline="\n")
    (repo / "schemas").mkdir()
    (repo / "schemas" / "s.json").write_text(json.dumps({"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}), encoding="utf-8", newline="\n")
    (repo / "config").mkdir()
    (repo / "docs" / "adr").mkdir(parents=True)
    (repo / "docs" / "adr" / "0001-queue.md").write_text("# ADR-0001: Queue\n", encoding="utf-8", newline="\n")
    env = dict(os.environ, HARNESS_ROOT=str(repo), SCHEMA_MAP="config:schemas/s.json", FRESH_REF="HEAD",
               PYTHONPATH=os.pathsep.join([str(SERVERS), os.environ.get("PYTHONPATH", "")]))
    os.environ.update({k: env[k] for k in ("HARNESS_ROOT", "SCHEMA_MAP", "FRESH_REF")})
    sys.path.insert(0, str(SERVERS))

    print("protocol (stdio, tools/list):")
    for n in NAMES:
        tools = protocol(n, env)
        check(n, len(tools) >= 2, ", ".join(tools))

    print("behavior:")
    m = {n: importlib.import_module(n) for n in NAMES}
    r1 = m["test_env_broker"].reserve_test_env("a1")
    r2 = m["test_env_broker"].reserve_test_env("a2")
    r3 = m["test_env_broker"].reserve_test_env("a3")
    check("test_env_broker: 2 slots, third agent waits", r1["status"] == "granted" and r2["status"] == "granted" and r3 == {"status": "queued", "position": 1})
    m["test_env_broker"].release_test_env("a1")
    check("test_env_broker: release gives the slot to the queue", m["test_env_broker"].reserve_test_env("a3")["status"] == "granted")

    se = m["safe_edit"]
    check("safe_edit: Red Zone refused", se.apply_edit(".env", "X=1", "test")["status"] == "refused")
    check("safe_edit: normal file written", se.apply_edit("src/a.txt", "hello\n", "test")["status"] == "written")
    try:
        se.preview_diff("../outside.txt", "x")
        check("safe_edit: path outside repo refused", False)
    except ValueError:
        check("safe_edit: path outside repo refused", True)

    sr = m["spec_registry"]
    check("spec_registry: lists ADR", any(s["id"] == "0001-queue" for s in sr.list_specs()))
    check("spec_registry: commit without Spec/ADR line blocks PR", sr.can_create_pr("HEAD")["allowed"] is False)

    cf = m["context_freshness"]
    check("context_freshness: fresh at HEAD", cf.is_context_fresh()["fresh"] is True)

    pr = m["pii_reader"]
    t = pr.read_masked("calls.txt")["text"]
    check("pii_reader: email and phone masked", "<email>" in t and "<phone>" in t and "ivan@" not in t, t.strip())

    ss = m["schema_store"]
    check("schema_store: invalid doc refused", ss.apply_patch("config/a.json", {"x": 1})["status"] == "refused")
    check("schema_store: valid doc written", ss.apply_patch("config/a.json", {"name": "ok"})["status"] == "written")

    rv = m["readonly_view"]
    check("readonly_view: reads core, has no write tool", rv.read_file("engine.txt")["text"] == "core logic" and not hasattr(rv, "write_file"))

    sch = m["slot_scheduler"]
    check("slot_scheduler: unknown resource refused", sch.request_slot("tpu", "a1")["status"] == "error")
    check("slot_scheduler: gpu slot granted", sch.request_slot("gpu", "a1")["status"] == "granted")

    rt = m["redteam_runner"]
    sc = rt.list_scenarios()
    check("redteam_runner: 25 scenarios", len(sc) == 25, f"{len(sc)}")
    check("redteam_runner: B01 blocked", rt.run_scenario("B01")["blocked"] is True)

    qg = m["quality_gate"]
    check("quality_gate: returns a result", "passed" in qg.run_quality_gate())

    print(f"\n{'FAIL' if fails else 'OK'}: {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
