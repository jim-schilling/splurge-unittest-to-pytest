#!/usr/bin/env python3
"""
Basic API Usage Example for splurge-unittest-to-pytest

This example demonstrates how to use the splurge-unittest-to-pytest API
programmatically to migrate unittest test suites to pytest format.

The API provides several key components:
- MigrationOrchestrator: Main orchestrator for migration
- MigrationConfig: Configuration for migration settings
- PipelineContext: Context for pipeline execution
- Result: Functional error handling with success/failure states
"""

from pathlib import Path

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator


def basic_migration_example():
    """Demonstrate basic API usage for single file migration."""

    print("=== Basic API Usage Example ===")
    print()

    # Create a simple unittest file for demonstration
    unittest_content = '''
import unittest

class TestMath(unittest.TestCase):
    def setUp(self):
        self.value = 10

    def tearDown(self):
        self.value = 0

    def test_addition(self):
        """Test basic addition."""
        result = 5 + 3
        self.assertEqual(result, 8)
        self.assertTrue(result > 0)

    def test_multiplication(self):
        """Test multiplication."""
        result = 4 * 2
        self.assertEqual(result, 8)
        self.assertIn(result, [8, 16, 32])

if __name__ == "__main__":
    unittest.main()
'''

    # Write the example unittest file
    example_file = Path("example_math_test.py")
    example_file.write_text(unittest_content)

    print("1. Created example unittest file: example_math_test.py")
    print()

    # Basic migration using the API
    print("2. Using the API for migration:")

    # Create migration orchestrator
    orchestrator = MigrationOrchestrator()

    # Create configuration (using defaults)
    config = MigrationConfig()

    print("   - Created MigrationOrchestrator")
    print("   - Created MigrationConfig with default settings")
    print()

    # Execute migration
    print("3. Executing migration...")
    result = orchestrator.migrate_file(str(example_file), config)

    # Handle the result
    if result.is_success():
        print("   ✅ Migration completed successfully!")
        print(f"   📄 Generated file: {result.data}")

        # Read and display the generated pytest file
        generated_file = Path(result.data)
        if generated_file.exists():
            print()
            print("=== Generated pytest file ===")
            print(generated_file.read_text())

            # Clean up
            generated_file.unlink()
            print("   🧹 Cleaned up generated file")
    else:
        print("   ❌ Migration failed!")
        print(f"   Error: {result.error}")

    print()
    example_file.unlink()
    print("   🧹 Cleaned up example file")


def configuration_example():
    """Demonstrate API configuration options."""

    print("=== Configuration Options ===")
    print()

    # Create custom configuration
    config = MigrationConfig(
        line_length=100,  # Set line length for formatting
        backup_originals=True,  # Create backup files
        verbose=True,  # Enable verbose logging
    )

    print("Custom configuration options:")
    print(f"   - line_length: {config.line_length}")
    print(f"   - backup_originals: {config.backup_originals}")
    print(f"   - verbose: {config.verbose}")
    print()

    print("Available configuration options:")
    print("   - line_length: int (default: 120)")
    print("   - backup_originals: bool (default: False)")
    print("   - verbose: bool (default: False)")
    print("   - fail_fast: bool (default: False)")
    print("   - output_dir: str | None (default: None)")


def directory_migration_example():
    """Demonstrate directory migration using the API."""

    print("=== Directory Migration ===")
    print()

    # Create a directory with multiple unittest files
    test_dir = Path("example_test_dir")
    test_dir.mkdir(exist_ok=True)

    # Create multiple unittest files
    test_files = {
        "test_arithmetic.py": """
import unittest

class TestArithmetic(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(2 + 2, 4)

    def test_subtraction(self):
        self.assertEqual(10 - 3, 7)
""",
        "test_strings.py": """
import unittest

class TestStrings(unittest.TestCase):
    def test_concatenation(self):
        result = "hello" + "world"
        self.assertEqual(result, "helloworld")
        self.assertIn("hello", result)
""",
        "test_collections.py": """
import unittest

class TestCollections(unittest.TestCase):
    def test_lists(self):
        items = [1, 2, 3]
        self.assertEqual(len(items), 3)
        self.assertIn(2, items)
""",
    }

    # Write test files
    for filename, content in test_files.items():
        (test_dir / filename).write_text(content)

    print(f"Created test directory with {len(test_files)} unittest files")
    print()

    # Migrate entire directory
    orchestrator = MigrationOrchestrator()
    config = MigrationConfig(verbose=True)

    print("Migrating entire directory...")
    result = orchestrator.migrate_directory(str(test_dir), config)

    if result.is_success():
        print("   ✅ Directory migration completed successfully!")
        print(f"   📄 Migrated files: {len(result.data)}")

        # Clean up
        for filename in test_files.keys():
            generated_file = Path(filename.replace(".py", ".py"))
            if generated_file.exists():
                generated_file.unlink()

        # Clean up the directory
        import shutil

        shutil.rmtree(test_dir)
        print("   🧹 Cleaned up generated files and directory")
    else:
        print("   ❌ Directory migration failed!")
        print(f"   Error: {result.error}")


def error_handling_example():
    """Demonstrate error handling with the API."""

    print("=== Error Handling ===")
    print()

    orchestrator = MigrationOrchestrator()

    # Try to migrate a non-existent file
    try:
        result = orchestrator.migrate_file("non_existent_file.py")
    except ValueError as e:
        print("   ✅ Migration failed as expected (ValueError raised)")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {e}")
        return

    if result.is_success():
        print("   ✅ Migration succeeded unexpectedly")
    else:
        print("   ✅ Migration failed as expected")
        print(f"   Error type: {type(result.error).__name__}")
        print(f"   Error message: {result.error}")

    print()
    print("Result object provides:")
    print("   - is_success(): bool")
    print("   - is_failure(): bool")
    print("   - is_warning(): bool")
    print("   - unwrap(): Get data or raise error")
    print("   - error: Exception object")
    print("   - warnings: List of warning messages")


def advanced_usage_example():
    """Show advanced API usage patterns."""

    print("=== Advanced API Usage ===")
    print()

    print("Pipeline customization:")
    print("   - Access individual pipeline steps")
    print("   - Create custom transformation jobs")
    print("   - Chain multiple transformations")
    print()

    print("Event-driven architecture:")
    print("   - Subscribe to migration events")
    print("   - Monitor progress and errors")
    print("   - Custom logging and reporting")
    print()

    print("Custom transformation:")
    print("   - Extend existing transformers")
    print("   - Add new assertion patterns")
    print("   - Create domain-specific transformations")
    print()

    print("Integration patterns:")
    print("   - Use with existing test suites")
    print("   - Integrate with CI/CD pipelines")
    print("   - Combine with other code quality tools")


if __name__ == "__main__":
    basic_migration_example()
    print("\n" + "=" * 50 + "\n")
    configuration_example()
    print("\n" + "=" * 50 + "\n")
    directory_migration_example()
    print("\n" + "=" * 50 + "\n")
    error_handling_example()
    print("\n" + "=" * 50 + "\n")
    advanced_usage_example()
