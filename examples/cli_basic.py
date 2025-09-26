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

    # Run version command
    print("Running: splurge-unittest-to-pytest version")
    result = subprocess.run(
        [sys.executable, "-m", "splurge_unittest_to_pytest.cli", "version"], capture_output=True, text=True, cwd="."
    )
    print(f"Output: {result.stdout.strip()}")
    print()

    # Run migration command
    print("Running: splurge-unittest-to-pytest migrate example_unittest.py --verbose")
    result = subprocess.run(
        [sys.executable, "-m", "splurge_unittest_to_pytest.cli", "migrate", "example_unittest.py", "--verbose"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    print("Migration completed!")
    print(f"Return code: {result.returncode}")
    if result.stdout:
        print(f"STDOUT: {result.stdout}")
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    print()

    # Check if output file was created
    output_file = Path("example_unittest.py")
    if output_file.exists():
        print("=== Generated pytest file content ===")
        print(output_file.read_text())
        print()

        # Clean up
        output_file.unlink()
        print("Cleaned up generated file")
    else:
        print("No output file generated")

    # Clean up the example file
    example_file.unlink()
    print("Cleaned up example file")


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
