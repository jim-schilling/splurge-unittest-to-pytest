#!/usr/bin/env python3
"""Clean CLI example that invokes the package CLI via subprocess.

This example prints version output and runs `migrate --dry-run --list`
to show what files the CLI would process. It uses subprocess so the
actual CLI entrypoint is exercised.
"""

import subprocess
import sys
from pathlib import Path


def _run_cli(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "splurge_unittest_to_pytest.cli"] + args
    print("$", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def run_cli_example() -> None:
    example_file = Path("example_unittest.py")
    example_file.write_text(
        """import unittest

class TestExample(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)
""",
        encoding="utf-8",
    )

    # Show version
    ver = _run_cli(["version"])
    print("--- VERSION STDOUT ---")
    print(ver.stdout or "<no stdout>")
    print("--- VERSION STDERR ---")
    print(ver.stderr or "<no stderr>")

    # Run migrate in dry-run mode
    mig = _run_cli(["migrate", "--dry-run", str(example_file)])
    print("--- MIGRATE STDOUT ---")
    if mig.stdout:
        print(mig.stdout)
    else:
        print(mig.stderr or "<no output; try running with --dry-run without --list>")

    try:
        example_file.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    run_cli_example()
