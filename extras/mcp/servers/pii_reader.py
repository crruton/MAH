"""pii-reader: read data that has personal information, with masks (was: call-transcript).

Forbids: access to emails, phone numbers, card numbers and IBANs without masks.
Env: PII_ROOT="data" (the agent reads only below this folder).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import os
import re

from _common import ROOT, rel, safe_path, server

PII_ROOT = (ROOT / os.environ.get("PII_ROOT", "data")).resolve()
MASKS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "<card>"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), "<iban>"),
    (re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d"), "<phone>"),
]
mcp = server("pii-reader")


def mask(text: str) -> str:
    for rx, sub in MASKS:
        text = rx.sub(sub, text)
    return text


@mcp.tool()
def read_masked(path: str, max_chars: int = 20000) -> dict:
    """Read a file below PII_ROOT. Personal data comes back masked."""
    p = safe_path(path, PII_ROOT)
    return {"path": rel(p, PII_ROOT), "text": mask(p.read_text(encoding="utf-8", errors="replace")[:max_chars])}


@mcp.tool()
def search_masked(query: str, limit: int = 20) -> list:
    """Find lines that contain query below PII_ROOT. Lines come back masked."""
    out = []
    for p in sorted(PII_ROOT.rglob("*")):
        if not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if query.lower() in line.lower():
                out.append({"path": rel(p, PII_ROOT), "line": n, "text": mask(line)[:300]})
                if len(out) >= limit:
                    return out
    return out


if __name__ == "__main__":
    mcp.run()
