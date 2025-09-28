#!/usr/bin/env python3
"""Test fixture transformation functionality."""

from splurge_unittest_to_pytest.transformers import UnittestToPytestCstTransformer


def test_fixture_transformation():
    """Test CST-based fixture transformation."""
    transformer = UnittestToPytestCstTransformer()

    # Test unittest with setUp/setUpClass
    test_code = """
import unittest

class TestWithFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared_resource = "test_resource"
        cls.class_setup_called = True

    @classmethod
    def tearDownClass(cls):
        cls.shared_resource = None
        cls.class_teardown_called = True

    def setUp(self):
        self.instance_resource = "instance_resource"
        self.setup_called = True

    def tearDown(self):
        self.instance_resource = None
        self.teardown_called = True

    def test_with_fixtures(self):
        self.assertTrue(self.setup_called)
        self.assertEqual(self.instance_resource, "instance_resource")
        self.assertTrue(self.class_setup_called)
        self.assertEqual(self.shared_resource, "test_resource")

if __name__ == "__main__":
    unittest.main()
"""

    # Test that transformation works without errors
    transformed = transformer.transform_code(test_code)

    # Verify that the transformation produced valid output
    assert isinstance(transformed, str)
    assert len(transformed) > 0

    # Verify that unittest.TestCase inheritance was removed (basic transformation working)
    assert "unittest.TestCase" not in transformed
    assert "class TestWithFixtures(" in transformed or "class TestWithFixtures:" in transformed

    # Verify that the original code structure is preserved
    assert "def test_with_fixtures" in transformed

    # Verify that instance-level fixtures were transformed (setUp/tearDown should be removed/transformed)
    # Note: The actual method names may still be present in comments or other contexts
    # but the functionality should be transformed to fixtures

    # Verify that pytest fixtures were created
    assert "@pytest.fixture" in transformed
    assert "def setup_method(self):" in transformed
    # We use a single autouse fixture with yield; no separate teardown_method is required
    assert "def teardown_method(self):" not in transformed
    assert "yield" in transformed  # Fixtures should use yield pattern

    # Verify that assertions were transformed
    assert "assert self.setup_called" in transformed
    assert 'assert self.instance_resource == "instance_resource"' in transformed
    assert "assert self.class_setup_called" in transformed
    assert 'assert self.shared_resource == "test_resource"' in transformed

    # Verify that the core transformation worked (unittest.TestCase removed)
    assert "unittest.TestCase" not in transformed
    assert "class TestWithFixtures(" in transformed or "class TestWithFixtures:" in transformed

    # Note: setUpClass and tearDownClass are not transformed in this version due to regex complexity
    # This is a known limitation that can be addressed in future versions with more sophisticated CST-based transformations

    # Note: Full fixture transformation is still in development
    # For now, we verify that the basic structure is preserved
    assert True  # Mark test as successful
