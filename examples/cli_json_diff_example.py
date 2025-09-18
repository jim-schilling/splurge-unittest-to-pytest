"""Example: run splurge CLI programmatically and parse NDJSON output.

This script runs the CLI in a subprocess and collects NDJSON lines. It is a small helper for CI pipelines.
"""

import json
import subprocess
from pathlib import Path

p = Path(".")
cmd = ["python", "-m", "splurge_unittest_to_pytest.cli", "--dry-run", "--json", "--diff", str(p)]
proc = subprocess.run(cmd, capture_output=True, text=True)
for line in proc.stdout.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
        print(f"{rec['path']}: changed={rec['changed']}")
    except Exception:
        # Non-json lines are printed to stderr or human-friendly output
        print(line)
