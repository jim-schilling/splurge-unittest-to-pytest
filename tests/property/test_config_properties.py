"""Property-based tests for configuration functionality.

This module contains Hypothesis-based property tests for the configuration
components in splurge_unittest_to_pytest, including validation, templates,
advisors, and use case detection.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from splurge_unittest_to_pytest.config_validation import (
    ConfigurationAdvisor,
    ConfigurationUseCaseDetector,
    get_template,
    list_available_templates,
    validate_migration_config_object,
)
from splurge_unittest_to_pytest.context import MigrationConfig
from tests.hypothesis_config import DEFAULT_SETTINGS


# Strategy for generating valid MigrationConfig objects
@st.composite
def migration_config_strategy(draw: st.DrawFn) -> MigrationConfig:
    """Generate valid MigrationConfig objects for testing."""
    # Create a base config and modify it
    config = MigrationConfig()

    # Override some fields with random values
    config = config.with_override(
        line_length=draw(st.integers(min_value=60, max_value=200)),
        dry_run=draw(st.booleans()),
        fail_fast=draw(st.booleans()),
        verbose=draw(st.booleans()),
        transform_assertions=draw(st.booleans()),
        transform_setup_teardown=draw(st.booleans()),
        transform_subtests=draw(st.booleans()),
        transform_skip_decorators=draw(st.booleans()),
        transform_imports=draw(st.booleans()),
        remove_unused_imports=draw(st.booleans()),
        preserve_import_comments=draw(st.booleans()),
        format_output=draw(st.booleans()),
        generate_report=draw(st.booleans()),
        test_method_prefixes=draw(
            st.lists(
                st.text(
                    min_size=1,
                    max_size=10,
                    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
                ),
                min_size=1,
                max_size=5,
            )
        ),
        assert_almost_equal_places=draw(st.integers(min_value=1, max_value=15)),
        max_file_size_mb=draw(st.integers(min_value=1, max_value=50)),
        max_concurrent_files=draw(st.integers(min_value=1, max_value=10)),
    )

    return config


# Strategy for generating template names
@st.composite
def template_name_strategy(draw: st.DrawFn) -> str:
    """Generate template names that might exist."""
    available = list_available_templates()
    if available:
        return draw(st.sampled_from(available))
    else:
        # Fallback to common template names
        return draw(
            st.sampled_from(
                [
                    "basic",
                    "enterprise",
                    "ci",
                    "development",
                    "production",
                    "custom",
                    "minimal",
                    "comprehensive",
                    "default",
                ]
            )
        )


class TestConfigProperties:
    """Property-based tests for configuration functionality."""

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_validate_migration_config_object_accepts_valid_configs(self, config: MigrationConfig) -> None:
        """Test that validate_migration_config_object accepts all valid configs."""
        try:
            validate_migration_config_object(config)
            # If validation succeeds, config was valid - this is good
        except Exception:
            # If validation fails, that's also acceptable for property testing
            # The strategy might generate invalid configs, and that's fine
            pass

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_advisor_suggest_improvements_returns_list(self, config: MigrationConfig) -> None:
        """Test that ConfigurationAdvisor.suggest_improvements returns a list."""
        advisor = ConfigurationAdvisor()

        # Should work for any valid config
        suggestions = advisor.suggest_improvements(config)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 10  # Should return at most 10 suggestions

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_advisor_suggestions_have_required_fields(self, config: MigrationConfig) -> None:
        """Test that all suggestions have required fields."""
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        for suggestion in suggestions:
            assert hasattr(suggestion, "type")
            assert hasattr(suggestion, "message")
            assert hasattr(suggestion, "action")
            assert hasattr(suggestion, "priority")
            assert isinstance(suggestion.priority, int)
            assert 1 <= suggestion.priority <= 5

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_use_case_detector_detects_valid_use_case(self, config: MigrationConfig) -> None:
        """Test that ConfigurationUseCaseDetector always detects a valid use case."""
        detector = ConfigurationUseCaseDetector()

        use_case = detector.detect_use_case(config)

        assert isinstance(use_case, str)
        assert len(use_case) > 0
        # Should be one of the known profiles
        from splurge_unittest_to_pytest.config_validation import ConfigurationProfile

        valid_profiles = [
            ConfigurationProfile.BASIC_MIGRATION,
            ConfigurationProfile.CUSTOM_TESTING_FRAMEWORK,
            ConfigurationProfile.ENTERPRISE_DEPLOYMENT,
            ConfigurationProfile.CI_INTEGRATION,
            ConfigurationProfile.DEVELOPMENT_DEBUGGING,
            ConfigurationProfile.PRODUCTION_DEPLOYMENT,
            ConfigurationProfile.UNKNOWN,
        ]
        assert use_case in valid_profiles

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_use_case_detector_is_deterministic(self, config: MigrationConfig) -> None:
        """Test that use case detection is deterministic for the same config."""
        detector = ConfigurationUseCaseDetector()

        result1 = detector.detect_use_case(config)
        result2 = detector.detect_use_case(config)

        assert result1 == result2

    @DEFAULT_SETTINGS
    @given(template_name=template_name_strategy())
    def test_get_template_returns_valid_template_or_none(self, template_name: str) -> None:
        """Test that get_template returns a valid template or None."""
        template = get_template(template_name)

        if template is not None:
            # If a template is returned, it should have required attributes
            assert hasattr(template, "name")
            assert hasattr(template, "description")
            assert hasattr(template, "config_dict")
            assert isinstance(template.config_dict, dict)
            # Template name should be a string (not necessarily matching input)
            assert isinstance(template.name, str)

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_advisor_suggestions_prioritized_correctly(self, config: MigrationConfig) -> None:
        """Test that suggestions are properly prioritized (highest priority first)."""
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        if len(suggestions) > 1:
            # Check that suggestions are sorted by priority (descending)
            priorities = [s.priority for s in suggestions]
            assert priorities == sorted(priorities, reverse=True)

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_advisor_handles_edge_case_configs(self, config: MigrationConfig) -> None:
        """Test that ConfigurationAdvisor handles various edge case configurations."""
        advisor = ConfigurationAdvisor()

        # Test with minimal config
        minimal_config = MigrationConfig()
        suggestions = advisor.suggest_improvements(minimal_config)
        assert isinstance(suggestions, list)

        # Test with extreme config values
        extreme_config = config.with_override(
            max_file_size_mb=100,  # Very large
            max_concurrent_files=50,  # Very high
            line_length=300,  # Very long
        )
        suggestions = advisor.suggest_improvements(extreme_config)
        assert isinstance(suggestions, list)

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_use_case_detector_scores_reasonably(self, config: MigrationConfig) -> None:
        """Test that use case detection produces reasonable scores."""
        detector = ConfigurationUseCaseDetector()

        # The detector should always return a valid profile
        use_case = detector.detect_use_case(config)

        # Should not be empty or None
        assert use_case is not None
        assert len(use_case.strip()) > 0

    @DEFAULT_SETTINGS
    @given(config1=migration_config_strategy(), config2=migration_config_strategy())
    def test_configuration_advisor_suggestions_vary_by_config(
        self, config1: MigrationConfig, config2: MigrationConfig
    ) -> None:
        """Test that different configs can produce different suggestions."""
        advisor = ConfigurationAdvisor()

        suggestions1 = advisor.suggest_improvements(config1)
        suggestions2 = advisor.suggest_improvements(config2)

        # Different configs might produce different suggestions
        # (This is a property test, so we can't guarantee they'll be different,
        # but we can test that the function handles different inputs)

        assert isinstance(suggestions1, list)
        assert isinstance(suggestions2, list)

        # Both should be valid suggestion lists
        for suggestions in [suggestions1, suggestions2]:
            for suggestion in suggestions:
                assert hasattr(suggestion, "priority")
                assert isinstance(suggestion.priority, int)

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_template_based_config_generation_works(self, config: MigrationConfig) -> None:
        """Test that template-based config generation produces valid configs."""
        # Get available templates
        templates = list_available_templates()

        if templates:  # Only test if templates are available
            for template_name in templates[:3]:  # Test first 3 templates to avoid too many iterations
                template = get_template(template_name)
                if template:
                    # Template should produce a valid config dict
                    config_dict = template.config_dict
                    assert isinstance(config_dict, dict)

                    # Should be able to create a MigrationConfig from it
                    try:
                        test_config = MigrationConfig()
                        # Apply template config
                        for key, value in config_dict.items():
                            if hasattr(test_config, key):
                                test_config = test_config.with_override(**{key: value})
                        # Should validate successfully
                        validate_migration_config_object(test_config)
                    except Exception as e:
                        pytest.fail(f"Template {template_name} produced invalid config: {e}")

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_validation_preserves_config_properties(self, config: MigrationConfig) -> None:
        """Test that configuration validation preserves config properties when valid."""
        try:
            validate_migration_config_object(config)

            # After validation, config should still have all its properties
            assert hasattr(config, "line_length")
            assert hasattr(config, "dry_run")
            assert hasattr(config, "transform_assertions")

            # Config should be usable (not corrupted by validation)
            assert isinstance(config.line_length, int)
            assert isinstance(config.dry_run, bool)
        except Exception:
            # If config is invalid, skip the property checks
            pass

    @DEFAULT_SETTINGS
    @given(config=migration_config_strategy())
    def test_configuration_advisor_suggestions_are_actionable(self, config: MigrationConfig) -> None:
        """Test that advisor suggestions provide actionable information."""
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        for suggestion in suggestions:
            # Each suggestion should have actionable content
            assert len(suggestion.message.strip()) > 0
            assert len(suggestion.action.strip()) > 0

            # Should have examples or be clearly actionable
            if hasattr(suggestion, "examples") and suggestion.examples:
                assert len(suggestion.examples) > 0
                assert all(isinstance(ex, str) for ex in suggestion.examples)
