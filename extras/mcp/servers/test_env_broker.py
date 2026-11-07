"""test-env-broker: lease shared test environments with a TTL and a FIFO queue.

Forbids: a direct connection to a shared test database without a lease.
Env: TEST_ENVS="test-db:2" (resource:capacity, comma separated).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os

from _common import Leases, server

CAP = {k: int(v) for k, v in (x.split(":") for x in os.environ.get("TEST_ENVS", "test-db:2").split(","))}
leases = Leases("test-env-broker", CAP)
mcp = server("test-env-broker")


@mcp.tool()
def reserve_test_env(agent_id: str, env: str = "test-db", ttl_sec: int = 600) -> dict:
    """Reserve a test environment. Returns the slot or a queue position."""
    return leases.acquire(env, agent_id, ttl_sec)


@mcp.tool()
def renew_test_env(agent_id: str, ttl_sec: int = 600) -> dict:
    """Extend the leases of agent_id (heartbeat). Call it while you work."""
    return leases.renew(agent_id, ttl_sec)


@mcp.tool()
def release_test_env(agent_id: str) -> dict:
    """Release all environments of agent_id."""
    return leases.release(agent_id)


@mcp.tool()
def queue_position(agent_id: str, env: str = "test-db") -> dict:
    """Position of agent_id in the queue. 0 means the agent holds a slot or does not wait."""
    return leases.position(env, agent_id)


if __name__ == "__main__":
    mcp.run()
