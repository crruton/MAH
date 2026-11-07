"""slot-scheduler: share scarce resources with leases (was: gpu-scheduler).

Forbids: use of a GPU, an LLM provider slot or a license without a lease.
Env: SLOTS="gpu:2,llm:8".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os

from _common import Leases, server

CAP = {k: int(v) for k, v in (x.split(":") for x in os.environ.get("SLOTS", "gpu:2,llm:8").split(","))}
leases = Leases("slot-scheduler", CAP)
mcp = server("slot-scheduler")


@mcp.tool()
def request_slot(resource: str, agent_id: str, ttl_sec: int = 300) -> dict:
    """Request a slot of a resource. Returns the slot or a queue position."""
    return leases.acquire(resource, agent_id, ttl_sec)


@mcp.tool()
def renew_slot(agent_id: str, ttl_sec: int = 300) -> dict:
    """Extend all slots of agent_id (heartbeat)."""
    return leases.renew(agent_id, ttl_sec)


@mcp.tool()
def release_slot(agent_id: str) -> dict:
    """Release all slots of agent_id."""
    return leases.release(agent_id)


@mcp.tool()
def query_queue_position(resource: str, agent_id: str) -> dict:
    """Position of agent_id in the queue of a resource."""
    return leases.position(resource, agent_id)


if __name__ == "__main__":
    mcp.run()
