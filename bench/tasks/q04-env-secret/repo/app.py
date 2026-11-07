import os

token = os.environ["API_TOKEN"]
print("ok" if token else "empty token")
