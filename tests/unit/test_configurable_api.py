"""Test the new configurable method pattern API."""

import pytest
from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


class TestConfigurableAPI:
    """Test the configurable method pattern API."""

    def test_default_patterns(self):
        """Test that default patterns are set correctly."""
        transformer = UnittestToPytestTransformer()

        # Check default setup patterns
        expected_setup = {
            "setup", "setUp", "set_up", "setup_method", "setUp_method",
            "before_each", "beforeEach", "before_test", "beforeTest"
        }
        assert transformer.setup_patterns == expected_setup

        # Check default teardown patterns
        expected_teardown = {
            "teardown", "tearDown", "tear_down", "teardown_method", "tearDown_method",
            "after_each", "afterEach", "after_test", "afterTest"
        }
        assert transformer.teardown_patterns == expected_teardown

        # Check default test patterns
        expected_test = {
            "test_", "test", "should_", "when_", "given_", "it_", "spec_"
        }
        assert transformer.test_patterns == expected_test

    def test_add_setup_pattern(self):
        """Test adding custom setup patterns."""
        transformer = UnittestToPytestTransformer()

        # Add custom pattern
        transformer.add_setup_pattern("before_all")

        # Verify it was added
        assert "before_all" in transformer.setup_patterns

        # Test that it works for method detection
        assert transformer._is_setup_method("before_all") is True
        assert transformer._is_setup_method("beforeAll") is True  # case insensitive

    def test_add_teardown_pattern(self):
        """Test adding custom teardown patterns."""
        transformer = UnittestToPytestTransformer()

        # Add custom pattern
        transformer.add_teardown_pattern("after_all")

        # Verify it was added
        assert "after_all" in transformer.teardown_patterns

        # Test that it works for method detection
        assert transformer._is_teardown_method("after_all") is True
        assert transformer._is_teardown_method("afterAll") is True  # case insensitive

    def test_add_test_pattern(self):
        """Test adding custom test patterns."""
        transformer = UnittestToPytestTransformer()

        # Add custom pattern
        transformer.add_test_pattern("describe_")

        # Verify it was added
        assert "describe_" in transformer.test_patterns

        # Test that it works for method detection
        assert transformer._is_test_method("describe_feature") is True

    def test_pattern_properties_return_copies(self):
        """Test that properties return copies, not references."""
        transformer = UnittestToPytestTransformer()

        # Get patterns
        setup_patterns = transformer.setup_patterns

        # Modify the returned set
        setup_patterns.add("custom_pattern")

        # Verify original is unchanged
        assert "custom_pattern" not in transformer.setup_patterns

    def test_invalid_pattern_inputs(self):
        """Test handling of invalid pattern inputs."""
        transformer = UnittestToPytestTransformer()

        # Test empty string
        transformer.add_setup_pattern("")
        transformer.add_setup_pattern("   ")
        transformer.add_teardown_pattern("")
        transformer.add_test_pattern("")

        # Should not add empty patterns
        assert "" not in transformer.setup_patterns
        assert "" not in transformer.teardown_patterns
        assert "" not in transformer.test_patterns

        # Test non-string inputs (should be handled gracefully)
        transformer.add_setup_pattern(None)  # type: ignore
        transformer.add_teardown_pattern(123)  # type: ignore
        transformer.add_test_pattern([])  # type: ignore

        # Should not crash and patterns should remain unchanged
        assert len(transformer.setup_patterns) > 0
        assert len(transformer.teardown_patterns) > 0
        assert len(transformer.test_patterns) > 0

    def test_method_detection_with_custom_patterns(self):
        """Test method detection works with custom patterns."""
        transformer = UnittestToPytestTransformer()

        # Add custom patterns
        transformer.add_setup_pattern("before_all")
        transformer.add_teardown_pattern("after_all")
        transformer.add_test_pattern("describe_")

        # Test setup detection
        assert transformer._is_setup_method("before_all") is True
        assert transformer._is_setup_method("beforeAll") is True

        # Test teardown detection
        assert transformer._is_teardown_method("after_all") is True
        assert transformer._is_teardown_method("afterAll") is True

        # Test method detection
        assert transformer._is_test_method("describe_feature") is True
        assert transformer._is_test_method("describe_") is True
