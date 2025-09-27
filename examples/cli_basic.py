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

from pathlib import Path

from splurge_unittest_to_pytest import main as main_module
from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestTransformer


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

    # First, run the CST/string transformer directly so we can reliably
    # show the transformed code (the orchestrator pipeline may currently
    # return the original input depending on pipeline composition).
    print("Running transformer directly: UnittestToPytestTransformer.transform_code(...)")
    src_text = example_file.read_text(encoding="utf-8")
    transformer = UnittestToPytestTransformer()
    transformed = transformer.transform_code(src_text)

    # Write and show transformed output
    direct_out = Path("example_unittest.transformed.py")
    direct_out.write_text(transformed, encoding="utf-8")
    print(f"Wrote direct transformed content to: {direct_out}")
    print("=== Direct transformed preview (first 2000 chars) ===")
    print(transformed[:2000])
    print()

    # Clean up the direct transformed file for the example
    try:
        direct_out.unlink()
    except Exception:
        pass

    # Also demonstrate the programmatic migration API as a fallback
    print("Running migration via programmatic API: main.migrate([...])")
    res = main_module.migrate([str(example_file)])

    if res.is_success():
        print("Programmatic migrate returned success (data preview):")
        print(res.data)
    else:
        print("Programmatic migrate returned error:")
        print(res.error)

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
