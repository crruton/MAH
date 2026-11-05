"""MCP server: lease test environments with a TTL and a FIFO queue.

Agents never connect to a shared test database directly; they reserve an environment,
renew the lease while working and release it. Expired leases are reclaimed, so a crashed
agent cannot block others. State lives in a JSON file guarded by a lock.
"""
import json
import os
import threading
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ENVS = [e.strip() for e in os.environ.get("TEST_ENVS", "test-db-1,test-db-2").split(",") if e.strip()]
STATE = Path(os.environ.get("BROKER_STATE", ".test_env_broker_state.json"))
MIN_TTL, MAX_TTL = 60, 3600
_lock = threading.Lock()
mcp = FastMCP("test-env-broker")


def _load() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"leases": {}, "queue": []}


def _save(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _reclaim(state: dict) -> None:
    now = time.time()
    state["leases"] = {env: lease for env, lease in state["leases"].items() if lease["expires_at"] > now}


def _ttl(ttl_sec: int) -> int:
    return max(MIN_TTL, min(ttl_sec, MAX_TTL))


@mcp.tool()
def reserve_test_env(agent_id: str, ttl_sec: int = 600) -> dict:
    """Reserve a free test environment for agent_id. Returns the environment or a queue position."""
    with _lock:
        state = _load()
        _reclaim(state)
        for env, lease in state["leases"].items():
            if lease["agent_id"] == agent_id:
                return {"status": "reserved", "env": env, "expires_at": lease["expires_at"]}
        queue = state["queue"]
        if agent_id not in queue:
            queue.append(agent_id)
        free = [e for e in ENVS if e not in state["leases"]]
        if free and queue[0] == agent_id:
            queue.pop(0)
            lease = {"agent_id": agent_id, "expires_at": time.time() + _ttl(ttl_sec)}
            state["leases"][free[0]] = lease
            _save(state)
            return {"status": "reserved", "env": free[0], "expires_at": lease["expires_at"]}
        _save(state)
        return {"status": "queued", "position": queue.index(agent_id) + 1}


@mcp.tool()
def renew_test_env(agent_id: str, ttl_sec: int = 600) -> dict:
    """Extend the lease held by agent_id (heartbeat)."""
    with _lock:
        state = _load()
        _reclaim(state)
        for env, lease in state["leases"].items():
            if lease["agent_id"] == agent_id:
                lease["expires_at"] = time.time() + _ttl(ttl_sec)
                _save(state)
                return {"status": "renewed", "env": env, "expires_at": lease["expires_at"]}
        return {"status": "not_reserved"}


@mcp.tool()
def release_test_env(agent_id: str) -> dict:
    """Release the environment held by agent_id and leave the queue."""
    with _lock:
        state = _load()
        released = [env for env, lease in state["leases"].items() if lease["agent_id"] == agent_id]
        for env in released:
            del state["leases"][env]
        state["queue"] = [a for a in state["queue"] if a != agent_id]
        _save(state)
        return {"status": "released", "envs": released}


@mcp.tool()
def queue_position(agent_id: str) -> dict:
    """Position of agent_id in the waiting queue; 0 if it holds an environment or is not queued."""
    with _lock:
        state = _load()
        _reclaim(state)
        if any(lease["agent_id"] == agent_id for lease in state["leases"].values()):
            return {"status": "reserved", "position": 0}
        queue = state["queue"]
        if agent_id in queue:
            return {"status": "queued", "position": queue.index(agent_id) + 1}
        return {"status": "none", "position": 0}


if __name__ == "__main__":
    mcp.run()
