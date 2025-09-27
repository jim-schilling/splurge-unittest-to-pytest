#!/usr/bin/env python3
"""
Basic CLI Usage Example for splurge-unittest-to-pytest

This example demonstrates how to use the splurge-unittest-to-pytest CLI
to migrate unittest test suites to pytest format.

The CLI provides several commands:
- migrate: Migrate unittest files to pytest format
- version: Show the version of unittest-to-pytest
- init-config: Initialize a configuration file with default settings
"""

import subprocess
import sys
from pathlib import Path


def run_cli_example():
    """Demonstrate basic CLI usage."""

    # Create a simple unittest file for demonstration
    unittest_content = '''
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42

    def tearDown(self):
        self.value = None

    def test_addition(self):
        """Test basic addition functionality."""
        result = 1 + 1
        self.assertEqual(result, 2)
        self.assertTrue(result > 0)

    def test_string_operations(self):
        """Test string operations."""
        text = "hello world"
        self.assertIn("hello", text)
        self.assertEqual(len(text), 11)

if __name__ == "__main__":
    unittest.main()
'''

    # Write the example unittest file
    example_file = Path("example_unittest.py")
    example_file.write_text(unittest_content)

    print("=== CLI Basic Usage Example ===")
    print()

    # Example 1: Basic migration
    print("1. Basic migration command:")
    print("   splurge-unittest-to-pytest migrate example_unittest.py")
    print()

    # Example 2: Migration with verbose output
    print("2. Migration with detailed logging:")
    print("   splurge-unittest-to-pytest migrate example_unittest.py --verbose")
    print()

    # Example 3: Migrate all unittest files in a directory
    print("3. Migrate all unittest files in current directory:")
    print("   splurge-unittest-to-pytest migrate .")
    print()

    # Example 4: Check version
    print("4. Check version:")
    print("   splurge-unittest-to-pytest version")
    print()

    # Example 5: Initialize configuration
    print("5. Initialize configuration file:")
    print("   splurge-unittest-to-pytest init-config")
    print()

    print("=== Running actual examples ===")
    print()

    # Run the real CLI using the module entrypoint so examples exercise
    # the actual command-line behavior instead of calling internal APIs.
    print("Running actual CLI: python -m splurge_unittest_to_pytest.cli migrate example_unittest.py")

    def run_cli_command(args: list[str]) -> None:
        cmd = [sys.executable, "-m", "splurge_unittest_to_pytest.cli"] + args
        print(f"\n$ {' '.join(cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as exc:
            print(f"Failed to run CLI command: {exc}")
            return

        print("--- STDOUT ---")
        print(proc.stdout or "<no stdout>")
        print("--- STDERR ---")
        print(proc.stderr or "<no stderr>")
        print(f"Exit code: {proc.returncode}")

    # Basic migration example
    run_cli_command(["migrate", str(example_file)])

    # Show version
    run_cli_command(["version"])

    # Attempt to locate and show the transformed output file. The pipeline
    # creates a target file by replacing the source suffix with '.pytest.py'
    # when no explicit target is requested.
    target_candidate = example_file.with_suffix(".pytest.py")
    if target_candidate.exists():
        print("\n=== Transformed file (preview) ===")
        try:
            print(target_candidate.read_text(encoding="utf-8")[:4000])
        except Exception as exc:
            print(f"Failed to read transformed file: {exc}")
    else:
        # Fallback: find any file that starts with the example stem and is
        # not the original or backup and print the first match.
        for p in Path(".").glob(f"{example_file.stem}*.py"):
            # skip original and backups
            if p == example_file or p.suffix.endswith(".backup"):
                continue
            try:
                print("\n=== Transformed file (fallback preview) ===")
                print(p.read_text(encoding="utf-8")[:4000])
                break
            except Exception:
                continue

    # Also clean up any backup file the orchestrator may have created
    backup_file = Path("example_unittest.py.backup")
    if backup_file.exists():
        try:
            backup_file.unlink()
            print("Cleaned up backup file")
        except Exception:
            print("Could not remove backup file")

    # Clean up the example file (if it exists)
    try:
        if example_file.exists():
            example_file.unlink()
            print("Cleaned up example file")
    except FileNotFoundError:
        print("Example file was already cleaned up or doesn't exist")


def show_advanced_cli_features():
    """Show advanced CLI features and options."""

    print("=== Advanced CLI Features ===")
    print()

    print("Configuration options (via config file or environment):")
    print("- Line length for code formatting")
    print("- Backup original files")
    print("- Verbose logging")
    print("- Fail-fast mode")
    print()

    print("Directory processing:")
    print("- Recursively process all unittest files")
    print("- Pattern matching for file selection")
    print("- Batch processing with progress reporting")
    print()

    print("Error handling:")
    print("- Continue on errors (default)")
    print("- Fail-fast on first error")
    print("- Detailed error reporting")
    print()

    print("Output options:")
    print("- In-place modification")
    print("- Output to different directory")
    print("- Backup original files")
    print()


if __name__ == "__main__":
    run_cli_example()
    show_advanced_cli_features()
