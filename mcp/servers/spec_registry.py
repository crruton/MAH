"""spec-registry: find specs and check that commits link to a spec or an ADR.

Forbids: a merge request with commits that have no `Spec:` or `ADR:` line.
Env: SPEC_DIRS="openspec/specs,docs/specs,docs/adr".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os
import re

from _common import ROOT, git, server

DIRS = [d for d in os.environ.get("SPEC_DIRS", "openspec/specs,docs/specs,docs/adr").split(",") if d]
LINK = re.compile(r"^(Spec|ADR):[ \t]*\S+", re.M | re.I)
mcp = server("spec-registry")


def _specs():
    for d in DIRS:
        base = ROOT / d
        if base.is_dir():
            yield from sorted(base.rglob("*.md"))


@mcp.tool()
def list_specs() -> list:
    """List spec and ADR files with their first heading."""
    out = []
    for p in _specs():
        title = next((l.lstrip("# ").strip() for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("#")), p.stem)
        out.append({"id": p.stem, "path": p.relative_to(ROOT).as_posix(), "title": title})
    return out


@mcp.tool()
def get_spec(spec_id: str) -> dict:
    """Get the text of one spec by its id (file name without .md)."""
    for p in _specs():
        if p.stem == spec_id:
            return {"id": spec_id, "path": p.relative_to(ROOT).as_posix(), "text": p.read_text(encoding="utf-8")}
    return {"error": f"no spec {spec_id}"}


@mcp.tool()
def can_create_pr(base: str = "origin/main") -> dict:
    """Check that each commit in base..HEAD has a `Spec:` or `ADR:` line."""
    shas = [s for s in git("rev-list", f"{base}..HEAD").splitlines() if s]
    missing = [s[:8] for s in shas if not LINK.search(git("log", "-1", "--format=%B", s))]
    return {"allowed": not missing and bool(shas), "commits": len(shas), "without_link": missing}


if __name__ == "__main__":
    mcp.run()
