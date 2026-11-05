"""Shared code for the harness MCP servers: SDK import, repository root, safe paths, leases."""
import fnmatch
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as Server

ROOT = Path(os.environ.get("HARNESS_ROOT", os.getcwd())).resolve()
STATE_DIR = Path(os.environ.get("HARNESS_STATE_DIR", ROOT / ".harness" / "state"))
RED_ZONE = [p.strip() for p in os.environ.get(
    "HARNESS_RED_ZONE",
    ".env,.env.*,*.pem,*.key,secrets/**,.githooks/**,.claude/**,gates/**,harness.lock,opencode.json",
).split(",") if p.strip()]


def bash() -> str:
    """Full path to bash. On Windows a bare "bash" starts WSL from System32, not Git Bash."""
    return shutil.which("bash") or "bash"


def server(name: str) -> "Server":
    return Server(name)


def safe_path(rel: str, root: Path = ROOT) -> Path:
    """Resolve rel inside root. Symlinks are resolved first, so a link cannot point outside root."""
    p = (root / rel).resolve()
    if p != root and root not in p.parents:
        raise ValueError(f"path is outside the allowed root: {rel}")
    return p


def rel(p: Path, root: Path = ROOT) -> str:
    return p.relative_to(root).as_posix()


def is_red(rel_path: str) -> bool:
    name = rel_path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(rel_path, g) or fnmatch.fnmatch(name, g) for g in RED_ZONE)


def git(*args: str, root: Path = ROOT) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


class Leases:
    """FIFO leases with a TTL over a fixed capacity, stored in a JSON file."""

    def __init__(self, name: str, capacity: dict):
        self.file = STATE_DIR / f"{name}.json"
        self.capacity = capacity
        self.lock = threading.Lock()

    def _load(self) -> dict:
        if self.file.exists():
            return json.loads(self.file.read_text(encoding="utf-8"))
        return {"leases": {}, "queues": {}}

    def _save(self, s: dict) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(s, indent=2), encoding="utf-8")

    @staticmethod
    def _reclaim(s: dict) -> None:
        now = time.time()
        s["leases"] = {k: v for k, v in s["leases"].items() if v["expires_at"] > now}

    def acquire(self, resource: str, agent_id: str, ttl: int) -> dict:
        if resource not in self.capacity:
            return {"status": "error", "error": f"unknown resource {resource}", "known": list(self.capacity)}
        ttl = max(30, min(int(ttl), 3600))
        with self.lock:
            s = self._load()
            self._reclaim(s)
            for key, v in s["leases"].items():
                if v["resource"] == resource and v["agent_id"] == agent_id:
                    return {"status": "granted", "slot": key, "expires_at": v["expires_at"]}
            q = s["queues"].setdefault(resource, [])
            if agent_id not in q:
                q.append(agent_id)
            used = {k for k, v in s["leases"].items() if v["resource"] == resource}
            free = [f"{resource}-{i}" for i in range(1, self.capacity[resource] + 1) if f"{resource}-{i}" not in used]
            if free and q[0] == agent_id:
                q.pop(0)
                s["leases"][free[0]] = {"resource": resource, "agent_id": agent_id, "expires_at": time.time() + ttl}
                self._save(s)
                return {"status": "granted", "slot": free[0], "expires_at": s["leases"][free[0]]["expires_at"]}
            self._save(s)
            return {"status": "queued", "position": q.index(agent_id) + 1}

    def renew(self, agent_id: str, ttl: int) -> dict:
        with self.lock:
            s = self._load()
            self._reclaim(s)
            mine = [k for k, v in s["leases"].items() if v["agent_id"] == agent_id]
            for k in mine:
                s["leases"][k]["expires_at"] = time.time() + max(30, min(int(ttl), 3600))
            self._save(s)
            return {"status": "renewed" if mine else "not_held", "slots": mine}

    def release(self, agent_id: str) -> dict:
        with self.lock:
            s = self._load()
            mine = [k for k, v in s["leases"].items() if v["agent_id"] == agent_id]
            for k in mine:
                del s["leases"][k]
            for q in s["queues"].values():
                while agent_id in q:
                    q.remove(agent_id)
            self._save(s)
            return {"status": "released", "slots": mine}

    def position(self, resource: str, agent_id: str) -> dict:
        with self.lock:
            s = self._load()
            self._reclaim(s)
            if any(v["agent_id"] == agent_id and v["resource"] == resource for v in s["leases"].values()):
                return {"status": "granted", "position": 0}
            q = s["queues"].get(resource, [])
            return {"status": "queued", "position": q.index(agent_id) + 1} if agent_id in q else {"status": "none", "position": 0}
