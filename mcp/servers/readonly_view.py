"""readonly-view: read a protected part of the system with no write tools (was: rtp-core-readonly).

Forbids: any write to the core. The server has no tool that writes.
Env: READONLY_ROOT="core".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os

from _common import ROOT, rel, safe_path, server

BASE = (ROOT / os.environ.get("READONLY_ROOT", "core")).resolve()
mcp = server("readonly-view")


@mcp.tool()
def list_files(subdir: str = ".") -> list:
    """List files below READONLY_ROOT."""
    d = safe_path(subdir, BASE)
    return [rel(p, BASE) for p in sorted(d.rglob("*")) if p.is_file()][:500]


@mcp.tool()
def read_file(path: str, max_chars: int = 20000) -> dict:
    """Read a file below READONLY_ROOT."""
    p = safe_path(path, BASE)
    return {"path": rel(p, BASE), "text": p.read_text(encoding="utf-8", errors="replace")[:max_chars]}


if __name__ == "__main__":
    mcp.run()
