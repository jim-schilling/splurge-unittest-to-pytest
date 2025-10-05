"""Tests for configuration metadata system."""

from pathlib import Path
from unittest.mock import patch

import pytest

from splurge_unittest_to_pytest.config_metadata import (
    ConfigurationField,
    ConfigurationMetadataRegistry,
    get_all_field_metadata,
    get_categories,
    get_field_metadata,
    get_fields_by_category,
    metadata_registry,
)


class TestConfigurationField:
    """Test ConfigurationField dataclass."""

    def test_to_dict(self):
        """Test converting ConfigurationField to dictionary."""
        field = ConfigurationField(
            name="test_field",
            type="str",
            description="Test description",
            examples=["example1", "example2"],
            constraints=["constraint1"],
            related_fields=["field1", "field2"],
            common_mistakes=["mistake1"],
            default_value="default",
            category="Test Category",
            importance="optional",
            cli_flag="--test-flag",
            environment_variable="TEST_VAR",
        )

        result = field.to_dict()

        expected = {
            "name": "test_field",
            "type": "str",
            "description": "Test description",
            "examples": ["example1", "example2"],
            "constraints": ["constraint1"],
            "related_fields": ["field1", "field2"],
            "common_mistakes": ["mistake1"],
            "default_value": "default",
            "category": "Test Category",
            "importance": "optional",
            "cli_flag": "--test-flag",
            "environment_variable": "TEST_VAR",
        }

        assert result == expected

    def test_minimal_field(self):
        """Test ConfigurationField with minimal required fields."""
        field = ConfigurationField(
            name="minimal",
            type="bool",
            description="Minimal field",
            examples=[],
            constraints=[],
            related_fields=[],
            common_mistakes=[],
            default_value=False,
            category="Test",
            importance="optional",
        )

        assert field.name == "minimal"
        assert field.cli_flag is None
        assert field.environment_variable is None


class TestConfigurationMetadataRegistry:
    """Test ConfigurationMetadataRegistry class."""

    def test_singleton_behavior(self):
        """Test that metadata_registry is a singleton instance."""
        registry1 = ConfigurationMetadataRegistry()
        registry2 = ConfigurationMetadataRegistry()

        # Should be different instances but same data
        assert registry1 is not registry2
        assert registry1.get_all_fields() == registry2.get_all_fields()

    def test_get_all_fields(self):
        """Test getting all fields."""
        registry = ConfigurationMetadataRegistry()
        fields = registry.get_all_fields()

        assert isinstance(fields, dict)
        assert len(fields) > 0

        # Check that all fields have required attributes
        for name, field in fields.items():
            assert isinstance(field, ConfigurationField)
            assert field.name == name
            assert field.description
            assert field.category
            assert field.importance in ["required", "recommended", "optional"]

    def test_get_categories(self):
        """Test getting all categories."""
        registry = ConfigurationMetadataRegistry()
        categories = registry.get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "Output Settings" in categories

    def test_get_fields_by_category(self):
        """Test getting fields by category."""
        registry = ConfigurationMetadataRegistry()
        output_fields = registry.get_fields_by_category("Output Settings")

        assert isinstance(output_fields, list)
        assert len(output_fields) > 0

        for field in output_fields:
            assert isinstance(field, ConfigurationField)
            assert field.category == "Output Settings"

    def test_get_field_metadata(self):
        """Test getting specific field metadata."""
        registry = ConfigurationMetadataRegistry()

        # Test existing field
        field = registry.get_field("target_root")
        assert field is not None
        assert field.name == "target_root"
        assert field.category == "Output Settings"

        # Test non-existing field
        field = registry.get_field("nonexistent_field")
        assert field is None

    def test_field_completeness(self):
        """Test that all fields have complete metadata."""
        registry = ConfigurationMetadataRegistry()
        fields = registry.get_all_fields()

        for field in fields.values():
            # All fields should have basic required attributes
            assert field.name
            assert field.type
            assert field.description
            assert field.category
            assert field.importance
            assert isinstance(field.examples, list)
            assert isinstance(field.constraints, list)
            assert isinstance(field.related_fields, list)
            assert isinstance(field.common_mistakes, list)

            # Importance should be valid
            assert field.importance in ["required", "recommended", "optional"]

    def test_categories_coverage(self):
        """Test that all fields are assigned to valid categories."""
        registry = ConfigurationMetadataRegistry()
        fields = registry.get_all_fields()
        categories = registry.get_categories()

        for field in fields.values():
            assert field.category in categories

    def test_cli_flags_uniqueness(self):
        """Test that CLI flags are unique across all fields."""
        registry = ConfigurationMetadataRegistry()
        fields = registry.get_all_fields()

        cli_flags = {}
        for field in fields.values():
            if field.cli_flag:
                assert field.cli_flag not in cli_flags, f"Duplicate CLI flag: {field.cli_flag}"
                cli_flags[field.cli_flag] = field.name

    def test_env_vars_uniqueness(self):
        """Test that environment variables are unique across all fields."""
        registry = ConfigurationMetadataRegistry()
        fields = registry.get_all_fields()

        env_vars = {}
        for field in fields.values():
            if field.environment_variable:
                assert field.environment_variable not in env_vars, f"Duplicate env var: {field.environment_variable}"
                env_vars[field.environment_variable] = field.name


class TestPublicAPI:
    """Test public API functions."""

    def test_get_all_field_metadata(self):
        """Test get_all_field_metadata function."""
        metadata = get_all_field_metadata()

        assert isinstance(metadata, dict)
        assert len(metadata) > 0

        for name, field in metadata.items():
            assert isinstance(field, ConfigurationField)
            assert field.name == name

    def test_get_categories(self):
        """Test get_categories function."""
        categories = get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert isinstance(categories[0], str)

    def test_get_fields_by_category(self):
        """Test get_fields_by_category function."""
        fields = get_fields_by_category("Output Settings")

        assert isinstance(fields, list)
        for field in fields:
            assert isinstance(field, ConfigurationField)
            assert field.category == "Output Settings"

    def test_get_field_metadata(self):
        """Test get_field_metadata function."""
        field = get_field_metadata("target_root")
        assert field is not None
        assert field.name == "target_root"

        field = get_field_metadata("nonexistent")
        assert field is None

    def test_metadata_registry_instance(self):
        """Test that metadata_registry is properly initialized."""
        assert isinstance(metadata_registry, ConfigurationMetadataRegistry)

        fields = metadata_registry.get_all_fields()
        assert len(fields) > 0
