"""Strip LEGACY sections from comparison files in tmp/comparisons.

Run this script from the repo root to update the generated comparison files so
they no longer contain the LEGACY section.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
COMP_DIR = TMP / "comparisons"

if not COMP_DIR.exists():
    print("No comparisons directory found, exiting.")
    raise SystemExit(0)

for p in COMP_DIR.glob("*.txt"):
    text = p.read_text(encoding="utf-8")
    parts = text.split("== LEGACY ==")
    if len(parts) == 1:
        # nothing to do
        continue
    # parts[0] = before LEGACY; parts[1] = legacy + rest
    # find start of STAGED within parts[1]
    rest = parts[1]
    staged_idx = rest.find("== STAGED ==")
    if staged_idx == -1:
        # malformed, skip
        print(f"Skipping {p}: no STAGED marker")
        continue
    new_text = parts[0].rstrip() + "\n\n" + rest[staged_idx:]
    p.write_text(new_text, encoding="utf-8")
    print(f"Updated {p}")

# also handle tmp/comparison_unittest_01.txt if present
single = TMP / "comparison_unittest_01.txt"
if single.exists():
    text = single.read_text(encoding="utf-8")
    parts = text.split("== LEGACY ==")
    if len(parts) > 1:
        rest = parts[1]
        staged_idx = rest.find("== STAGED ==")
        if staged_idx != -1:
            new_text = parts[0].rstrip() + "\n\n" + rest[staged_idx:]
            single.write_text(new_text, encoding="utf-8")
            print(f"Updated {single}")

print("Done.")
