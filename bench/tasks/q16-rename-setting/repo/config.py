import json


def load(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {"host": data["host"], "timeout": int(data.get("timeout", 30))}
