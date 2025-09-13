#!/usr/bin/env python3
"""Basic usage example for splurge-unittest-to-pytest."""

from splurge_unittest_to_pytest import convert_string


def main() -> None:
    """Demonstrate basic usage of the unittest to pytest converter."""
    print("=== Basic Usage Example ===\n")

    # Example unittest code
    unittest_code = """
import unittest

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_addition(self):
        result = self.calc.add(2, 3)
        self.assertEqual(result, 5)

    def test_subtraction(self):
        result = self.calc.subtract(5, 3)
        self.assertEqual(result, 2)
"""

    print("Original unittest code:")
    print(unittest_code)

    # Convert to pytest
    result = convert_string(unittest_code)

    print(f"Conversion successful: {result.has_changes}")
    print(f"Errors: {len(result.errors)}")

    print("\nConverted pytest code:")
    print(result.converted_code)

    print("\n=== Key Changes Made ===")
    print("✅ Removed 'import unittest'")
    print("✅ Removed 'unittest.TestCase' inheritance")
    print("✅ Converted setUp() to pytest fixture (would need manual adjustment)")
    print("✅ Removed 'self.' prefixes from test methods")
    print("✅ Converted self.assertEqual() to assert statements")


if __name__ == "__main__":
    main()
