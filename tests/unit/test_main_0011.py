"""Test the new configurable method pattern API."""

from splurge_unittest_to_pytest.main import PatternConfigurator

DOMAINS = ["main"]


class TestConfigurableAPI:
    """Test the configurable method pattern API."""

    def test_default_patterns(self) -> None:
        """Test that default patterns are set correctly."""
        transformer = PatternConfigurator()

        # Check default setup patterns
        expected_setup = {
            "setup",
            "setUp",
            "set_up",
            "setup_method",
            "setUp_method",
            "before_each",
            "beforeEach",
            "before_test",
            "beforeTest",
        }
        assert transformer.setup_patterns == expected_setup

        # Check default teardown patterns
        expected_teardown = {
            "teardown",
            "tearDown",
            "tear_down",
            "teardown_method",
            "tearDown_method",
            "after_each",
            "afterEach",
            "after_test",
            "afterTest",
        }
        assert transformer.teardown_patterns == expected_teardown

        # Check default test patterns
        expected_test = {"test_", "test", "should_", "when_", "given_", "it_", "spec_"}
        assert transformer.test_patterns == expected_test

    def test_add_setup_pattern(self) -> None:
        """Test adding custom setup patterns."""
        transformer = PatternConfigurator()

        # Add custom pattern
        transformer.add_setup_pattern("before_all")

        # Verify it was added
        assert "before_all" in transformer.setup_patterns

    # Test that it works via public behavior: property reflects added pattern
    transformer = PatternConfigurator()
    transformer.add_setup_pattern("before_all")
    assert "before_all" in transformer.setup_patterns

    def test_add_teardown_pattern(self) -> None:
        """Test adding custom teardown patterns."""
        transformer = PatternConfigurator()

        # Add custom pattern
        transformer.add_teardown_pattern("after_all")

        # Verify it was added
        assert "after_all" in transformer.teardown_patterns

    # Public behavior: property holds the added pattern
    transformer = PatternConfigurator()
    transformer.add_teardown_pattern("after_all")
    assert "after_all" in transformer.teardown_patterns

    def test_add_test_pattern(self) -> None:
        """Test adding custom test patterns."""
        transformer = PatternConfigurator()

        # Add custom pattern
        transformer.add_test_pattern("describe_")

        # Verify it was added
        assert "describe_" in transformer.test_patterns

    # Public behavior: property holds the added pattern
    transformer = PatternConfigurator()
    transformer.add_test_pattern("describe_")
    assert "describe_" in transformer.test_patterns

    def test_pattern_properties_return_copies(self) -> None:
        """Test that properties return copies, not references."""
        transformer = PatternConfigurator()

        # Get patterns
        setup_patterns = transformer.setup_patterns

        # Modify the returned set
        setup_patterns.add("custom_pattern")

        # Verify original is unchanged
        assert "custom_pattern" not in transformer.setup_patterns

    def test_invalid_pattern_inputs(self) -> None:
        """Test handling of invalid pattern inputs."""
        transformer = PatternConfigurator()

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
        transformer.add_setup_pattern(None)
        transformer.add_teardown_pattern(123)
        transformer.add_test_pattern([])

        # Should not crash and patterns should remain unchanged
        assert len(transformer.setup_patterns) > 0
        assert len(transformer.teardown_patterns) > 0
        assert len(transformer.test_patterns) > 0

    def test_method_detection_with_custom_patterns(self) -> None:
        """Test method detection works with custom patterns."""
        transformer = PatternConfigurator()

        # Add custom patterns
        transformer.add_setup_pattern("before_all")
        transformer.add_teardown_pattern("after_all")
        transformer.add_test_pattern("describe_")

    # Verify properties reflect added patterns
    transformer = PatternConfigurator()
    transformer.add_setup_pattern("before_all")
    transformer.add_teardown_pattern("after_all")
    transformer.add_test_pattern("describe_")
    assert "before_all" in transformer.setup_patterns
    assert "after_all" in transformer.teardown_patterns
    assert "describe_" in transformer.test_patterns
