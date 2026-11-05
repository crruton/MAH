"""schema-store: change structured files only when they stay valid (was: dialog-scenario-store).

Forbids: a text edit of a JSON file that breaks its JSON Schema.
Env: SCHEMA_MAP="config/scenarios:schemas/scenario.schema.json" (folder:schema, comma separated).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import json
import os

from _common import ROOT, rel, safe_path, server

try:
    import jsonschema
except ImportError:
    jsonschema = None

MAP = [x.split(":", 1) for x in os.environ.get("SCHEMA_MAP", "").split(",") if ":" in x]
mcp = server("schema-store")


def _schema_for(path):
    r = rel(path)
    for folder, schema in MAP:
        if r.startswith(folder.rstrip("/") + "/"):
            return json.loads(safe_path(schema).read_text(encoding="utf-8"))
    return None


def _validate(path, doc):
    schema = _schema_for(path)
    if schema is None:
        return ["no schema for this path: add it to SCHEMA_MAP"]
    if jsonschema is None:
        return ["install jsonschema to validate"]
    return [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]


@mcp.tool()
def get_doc(path: str) -> dict:
    """Read a JSON document."""
    p = safe_path(path)
    return {"path": rel(p), "doc": json.loads(p.read_text(encoding="utf-8"))}


@mcp.tool()
def propose_patch(path: str, new_doc: dict) -> dict:
    """Validate new_doc against the schema of path. Writes nothing."""
    p = safe_path(path)
    errors = _validate(p, new_doc)
    return {"path": rel(p), "valid": not errors, "errors": errors}


@mcp.tool()
def apply_patch(path: str, new_doc: dict) -> dict:
    """Write new_doc only when it is valid against the schema."""
    p = safe_path(path)
    errors = _validate(p, new_doc)
    if errors:
        return {"status": "refused", "errors": errors}
    p.write_text(json.dumps(new_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "written", "path": rel(p)}


if __name__ == "__main__":
    mcp.run()
