import os, sys
if os.path.exists("out/build/stale.lock"):
    sys.exit("build failed: out/build/stale.lock exists")
os.makedirs("out/build", exist_ok=True)
open("out/build/app.txt", "w", encoding="utf-8").write("built\n")
print("build ok")
