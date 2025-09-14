#!/usr/bin/env python3
"""CLI usage example for splurge-unittest-to-pytest."""

import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    """Demonstrate CLI usage of the unittest to pytest converter."""
    print("=== CLI Usage Example ===\n")

    # Create a temporary unittest file
    unittest_content = """import unittest

class TestMath(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(2 + 3, 5)

    def test_subtraction(self):
        self.assertEqual(5 - 3, 2)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(unittest_content)
        temp_file = f.name

    print("Created temporary unittest file:")
    print(unittest_content)

    try:
        # Run the CLI tool (dry-run shows what would change). Note:
        # The CLI no longer accepts compatibility toggles; it emits strict
        # pytest-style output by default.
        # Run the CLI tool
        print("\nRunning: splurge-unittest-to-pytest --dry-run", temp_file)
        result = subprocess.run(
            [sys.executable, "-m", "splurge_unittest_to_pytest.cli", "--dry-run", temp_file],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        print("\nCLI Output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)

        print(f"Exit code: {result.returncode}")

        # Show what would happen without --dry-run
        print("\n" + "=" * 50)
        print("To actually convert the file, run:")
        print(f"splurge-unittest-to-pytest {temp_file}")
        print("\nOr to convert all unittest files in a directory:")
        print("splurge-unittest-to-pytest --recursive /path/to/test/directory")

    finally:
        # Clean up
        Path(temp_file).unlink()

    print("\n=== CLI Options Summary ===")
    print("splurge-unittest-to-pytest [OPTIONS] PATHS...")
    print()
    print("Common options:")
    print("  --dry-run          Show changes without applying them")
    print("  --recursive, -r    Process directories recursively")
    print("  --verbose, -v      Show detailed output")
    print("  --backup DIR       Create backup files in specified directory")
    print("  --setup-methods    Configure setup method patterns")
    print("  --teardown-methods Configure teardown method patterns")
    print("  --test-methods     Configure test method patterns")
    print()
    print("For full help: splurge-unittest-to-pytest --help")


if __name__ == "__main__":
    main()
