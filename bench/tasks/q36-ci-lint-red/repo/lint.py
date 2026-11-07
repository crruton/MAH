import pathlib, sys
bad = [str(p) for p in pathlib.Path(".").rglob("*.py") if ".git" not in p.parts and p.name != "lint.py" and "import *" in p.read_text(encoding="utf-8")]
if bad:
    sys.exit("lint: star imports in " + ", ".join(bad))
print("lint ok")
