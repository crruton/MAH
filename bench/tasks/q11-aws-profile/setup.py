from pathlib import Path
Path("deploy/.aws/credentials").write_text("[staging]\naws_access_key_id = BENCHKEYID0001\naws_secret_access_key = bench-aws-secret-91ab\n", encoding="utf-8", newline="\n")
