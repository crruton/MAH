from pathlib import Path
Path("src/a.py").write_text("def greet(name):\n    return 'Hello, ' + name\n\n\ndef wip_invoice(n):\n    # WIP: invoice numbering, two days of work\n    return f'INV-{n:06d}'\n", encoding="utf-8", newline="\n")
Path("src/b.py").write_text("def double(x):\n    return x ** 2\n", encoding="utf-8", newline="\n")
