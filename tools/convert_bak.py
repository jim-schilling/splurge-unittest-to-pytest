from pathlib import Path

from splurge_unittest_to_pytest.main import convert_file

INPUT_DIR = Path("tests/data")
OUT_DIR = INPUT_DIR / "generated_from_bak"
OUT_DIR.mkdir(parents=True, exist_ok=True)

for p in [INPUT_DIR / "test_cli.py.bak.txt", INPUT_DIR / "test_init_api.py.bak.txt"]:
    if not p.exists():
        print(f"Missing {p}")
        continue
    out = OUT_DIR / p.name.replace(".bak.txt", ".py")
    print("Converting", p, "->", out)
    res = convert_file(str(p), output_path=str(out), autocreate=True)
    if res.errors:
        print("Errors converting:", res.errors)
    else:
        print("Wrote:", out)
