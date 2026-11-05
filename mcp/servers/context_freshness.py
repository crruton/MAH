"""context-freshness: stop work on an old copy of the repository.

Forbids: a plan or a change that starts from an old snapshot.
Env: FRESH_REF="origin/dev", FRESH_FETCH=1 to run git fetch before the check.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os

from _common import git, server

REF = os.environ.get("FRESH_REF", "origin/dev")
mcp = server("context-freshness")


def _fetch():
    if os.environ.get("FRESH_FETCH") == "1":
        git("fetch", "--quiet")


@mcp.tool()
def get_repo_snapshot_hash() -> dict:
    """Get HEAD and the reference commit. Keep the hash at the start of a task."""
    _fetch()
    return {"head": git("rev-parse", "HEAD"), "ref": REF, "ref_hash": git("rev-parse", REF)}


@mcp.tool()
def is_context_fresh(snapshot_hash: str = "") -> dict:
    """True when the reference branch has no commits that your snapshot does not have."""
    _fetch()
    base = snapshot_hash or git("rev-parse", "HEAD")
    behind = [s for s in git("rev-list", f"{base}..{REF}").splitlines() if s]
    return {"fresh": not behind, "behind_by": len(behind), "ref": REF}


@mcp.tool()
def refresh_context(snapshot_hash: str = "") -> dict:
    """List the files that changed on the reference branch after your snapshot. Read them again."""
    _fetch()
    base = snapshot_hash or git("rev-parse", "HEAD")
    files = [f for f in git("diff", "--name-only", f"{base}...{REF}").splitlines() if f]
    return {"changed_files": files, "ref": REF}


if __name__ == "__main__":
    mcp.run()
