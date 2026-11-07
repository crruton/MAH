import json, pathlib, runpy
applied = json.loads(pathlib.Path("applied.json").read_text(encoding="utf-8"))
schema = json.loads(pathlib.Path("schema.json").read_text(encoding="utf-8"))
for p in sorted(pathlib.Path("migrations").glob("0*.py")):
    if p.stem in applied:
        continue
    runpy.run_path(str(p))["up"](schema)
    applied.append(p.stem)
pathlib.Path("schema.json").write_text(json.dumps(schema), encoding="utf-8")
pathlib.Path("applied.json").write_text(json.dumps(applied), encoding="utf-8")
print(sorted(schema["users"]))
