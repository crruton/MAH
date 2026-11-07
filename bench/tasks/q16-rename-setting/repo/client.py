from config import load


def describe(path):
    cfg = load(path)
    return f"{cfg['host']} with timeout {cfg['timeout']}s"
