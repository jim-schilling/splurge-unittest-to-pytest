from pathlib import Path
import sys

files = [
    Path("tests/data/generated_from_bak/test_cli.py.py"),
    Path("tests/data/generated_from_bak/test_init_api.py.py"),
]

ok = True
for p in files:
    print("Checking", p)
    if not p.exists():
        print("  MISSING")
        ok = False
        continue
    src = p.read_text(encoding="utf-8")
    try:
        compile(src, str(p), "exec")
        print("  OK: syntactically valid")
    except Exception as e:
        print("  ERROR:", type(e).__name__, e)
        ok = False

if not ok:
    sys.exit(2)
print("All checks passed")
