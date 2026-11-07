import os


def load_key():
    path = os.path.join(os.path.dirname(__file__), ".env")
    for line in open(path, encoding="utf-8"):
        if line.startswith("API_KEY="):
            return line.strip().split("=", 1)[1]


def headers():
    return {"X-Api-Key": load_key()}
