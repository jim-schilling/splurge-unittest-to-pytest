#!/usr/bin/env python3
"""Small API examples for splurge-unittest-to-pytest.

These examples exercise the public programmatic API in a minimal way.
They are intended for documentation and quick manual testing.
"""

from pathlib import Path

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator


def basic_migration_example() -> None:
    """Create a tiny unittest file, run migration in dry-run, and print code."""

    unittest_content = """
import unittest

class TestMath(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(5 + 3, 8)

    def test_multiplication(self):
        self.assertEqual(4 * 2, 8)
"""

    example_file = Path("example_math_test.py")
    example_file.write_text(unittest_content, encoding="utf-8")

    orchestrator = MigrationOrchestrator()
    config = MigrationConfig(dry_run=True, backup_originals=False)

    result = orchestrator.migrate_file(str(example_file), config)

    if result.is_success():
        meta = getattr(result, "metadata", {}) or {}
        gen = meta.get("generated_code") or {}
        if isinstance(gen, dict):
            for path, code in gen.items():
                print(f"=== Generated: {path} ===")
                print(code)
        else:
            print("<no generated code available>")
    else:
        print(f"Migration failed: {result.error}")

    try:
        example_file.unlink()
    except Exception:
        pass


def configuration_example() -> None:
    """Show a couple of MigrationConfig defaults."""

    cfg = MigrationConfig()
    print("MigrationConfig defaults:")
    print(f"  line_length: {cfg.line_length}")
    print(f"  backup_originals: {cfg.backup_originals}")
    print(f"  dry_run: {cfg.dry_run}")


if __name__ == "__main__":
    basic_migration_example()
    configuration_example()
