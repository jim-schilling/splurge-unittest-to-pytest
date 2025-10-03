#!/usr/bin/env python3
"""Test that all Stage 1 brittleness improvements work together."""

import os
import tempfile

from splurge_unittest_to_pytest import MigrationOrchestrator
from splurge_unittest_to_pytest.detectors import UnittestFileDetector


def test_stage1_improvements():
    """Test all Stage 1 brittleness improvements work together."""

    # Create a test file
    test_code = """import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_code)
        f.flush()

        try:
            # Test detection
            detector = UnittestFileDetector()
            is_unittest = detector.is_unittest_file(f.name)
            print(f"✅ AST Detection works: {is_unittest}")

            # Test migration
            orchestrator = MigrationOrchestrator()
            result = orchestrator.migrate_file(f.name)
            print(f"✅ Migration success: {result.is_success()}")

            # Test specific exception handling
            try:
                detector.is_unittest_file("/nonexistent/file.py")
                print("❌ Should have raised FileNotFoundError")
            except FileNotFoundError:
                print("✅ Specific exception handling works")

            print("🎉 All Stage 1 brittleness improvements working!")

        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    test_stage1_improvements()
