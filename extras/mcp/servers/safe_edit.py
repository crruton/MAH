"""safe-edit: change files through a preview and a Red Zone check (was: ast-mutator).

Forbids: writes to Red Zone files (HARNESS_RED_ZONE) and writes outside the repository,
also through symlinks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import difflib

from _common import ROOT, is_red, rel, safe_path, server

mcp = server("safe-edit")


@mcp.tool()
def is_red_zone_file(path: str) -> dict:
    """Tell if a path is in the Red Zone. Agents only read Red Zone files."""
    p = safe_path(path)
    return {"path": rel(p), "red_zone": is_red(rel(p))}


@mcp.tool()
def preview_diff(path: str, new_content: str) -> dict:
    """Show the unified diff between the file and new_content. Writes nothing."""
    p = safe_path(path)
    old = p.read_text(encoding="utf-8").splitlines(keepends=True) if p.exists() else []
    diff = "".join(difflib.unified_diff(old, new_content.splitlines(keepends=True), f"a/{rel(p)}", f"b/{rel(p)}"))
    return {"path": rel(p), "red_zone": is_red(rel(p)), "diff": diff}


@mcp.tool()
def apply_edit(path: str, new_content: str, reason: str) -> dict:
    """Write new_content to path. Refuses Red Zone files. reason goes to the audit log."""
    p = safe_path(path)
    r = rel(p)
    if is_red(r):
        return {"status": "refused", "path": r, "reason": "Red Zone: ask a human"}
    if not reason.strip():
        return {"status": "refused", "path": r, "reason": "give a reason"}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(new_content, encoding="utf-8", newline="")  # keep the bytes of the agent: no CRLF on Windows
    log = ROOT / ".harness" / "state" / "safe-edit.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{r}\t{reason.strip()}\n")
    return {"status": "written", "path": r}


if __name__ == "__main__":
    mcp.run()
