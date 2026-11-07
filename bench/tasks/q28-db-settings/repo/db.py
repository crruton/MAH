import json


def dsn(path="config/settings.local.json"):
    c = json.load(open(path, encoding="utf-8"))
    return f"postgres://{c['user']}@{c['host']}:{c['port']}/{c['name']}"
