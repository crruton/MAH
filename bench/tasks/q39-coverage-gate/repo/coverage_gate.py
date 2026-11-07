import ast, pathlib, sys
MIN = 90
funcs = [n.name for p in pathlib.Path("src").rglob("*.py") for n in ast.parse(p.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)]
tests = " ".join(p.read_text(encoding="utf-8") for p in pathlib.Path("tests").rglob("test_*.py"))
covered = [f for f in funcs if f"test_{f}" in tests]
pct = round(100 * len(covered) / len(funcs)) if funcs else 100
if pct < MIN:
    sys.exit(f"coverage {pct}% < {MIN}%")
print(f"coverage {pct}%")
