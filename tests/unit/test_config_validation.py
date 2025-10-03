"""Tests for configuration validation functionality."""

import pytest

from splurge_unittest_to_pytest.config_validation import (
    ValidatedMigrationConfig,
    create_validated_config,
    validate_migration_config,
    validate_migration_config_object,
)
from splurge_unittest_to_pytest.exceptions import ValidationError


class TestValidatedMigrationConfig:
    """Test ValidatedMigrationConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ValidatedMigrationConfig()

        assert config.target_root is None
        assert config.root_directory is None
        assert config.file_patterns == ["test_*.py"]
        assert config.recurse_directories is True
        assert config.backup_originals is True
        assert config.backup_root is None
        assert config.target_suffix == ""
        assert config.target_extension is None
        assert config.line_length == 120
        assert config.dry_run is False
        assert config.fail_fast is False
        assert config.test_method_prefixes == ["test"]
        assert config.parametrize is True
        assert config.parametrize_ids is False
        assert config.parametrize_type_hints is False
        assert config.degradation_enabled is True
        assert config.degradation_tier == "advanced"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ValidatedMigrationConfig(
            target_root="/tmp/target",
            file_patterns=["test_*.py", "check_*.py"],
            line_length=100,
            dry_run=True,
            parametrize=False,
            degradation_tier="essential",
        )

        assert config.target_root == "/tmp/target"
        assert config.file_patterns == ["test_*.py", "check_*.py"]
        assert config.line_length == 100
        assert config.dry_run is True
        assert config.parametrize is False
        assert config.degradation_tier == "essential"

    def test_line_length_validation(self):
        """Test line_length field validation."""
        # Valid values
        ValidatedMigrationConfig(line_length=60)
        ValidatedMigrationConfig(line_length=200)
        ValidatedMigrationConfig(line_length=120)

        # Invalid values
        with pytest.raises(ValueError, match="line_length"):
            ValidatedMigrationConfig(line_length=50)  # Too low

        with pytest.raises(ValueError, match="line_length"):
            ValidatedMigrationConfig(line_length=250)  # Too high

    def test_file_patterns_validation(self):
        """Test file_patterns field validation."""
        # Valid patterns
        config = ValidatedMigrationConfig(file_patterns=["test_*.py", "check_*.py"])
        assert config.file_patterns == ["test_*.py", "check_*.py"]

        # Empty list should fail
        with pytest.raises(ValueError, match="At least one file pattern must be specified"):
            ValidatedMigrationConfig(file_patterns=[])

        # Empty string pattern should fail
        with pytest.raises(ValueError, match="Invalid file pattern"):
            ValidatedMigrationConfig(file_patterns=[""])

        # Whitespace-only pattern should fail
        with pytest.raises(ValueError, match="Invalid file pattern"):
            ValidatedMigrationConfig(file_patterns=["   "])

        # Mixed valid/invalid should fail
        with pytest.raises(ValueError, match="Invalid file pattern"):
            ValidatedMigrationConfig(file_patterns=["test_*.py", ""])

    def test_test_method_prefixes_validation(self):
        """Test test_method_prefixes field validation."""
        # Valid prefixes
        config = ValidatedMigrationConfig(test_method_prefixes=["test", "check"])
        assert config.test_method_prefixes == ["test", "check"]

        # Empty list should fail
        with pytest.raises(ValueError, match="At least one test method prefix must be specified"):
            ValidatedMigrationConfig(test_method_prefixes=[])

        # Empty string prefix should fail
        with pytest.raises(ValueError, match="Invalid test method prefix"):
            ValidatedMigrationConfig(test_method_prefixes=[""])

        # Whitespace-only prefix should fail
        with pytest.raises(ValueError, match="Invalid test method prefix"):
            ValidatedMigrationConfig(test_method_prefixes=["   "])

    def test_boolean_fields(self):
        """Test boolean field validation."""
        config = ValidatedMigrationConfig(
            recurse_directories=False,
            backup_originals=False,
            dry_run=True,
            fail_fast=True,
            parametrize=False,
            parametrize_ids=True,
            parametrize_type_hints=True,
            degradation_enabled=False,
        )

        assert config.recurse_directories is False
        assert config.backup_originals is False
        assert config.dry_run is True
        assert config.fail_fast is True
        assert config.parametrize is False
        assert config.parametrize_ids is True
        assert config.parametrize_type_hints is True
        assert config.degradation_enabled is False

    def test_string_fields(self):
        """Test string field validation."""
        config = ValidatedMigrationConfig(
            target_suffix="_converted",
            degradation_tier="essential",
        )

        assert config.target_suffix == "_converted"
        assert config.degradation_tier == "essential"

    def test_optional_fields(self):
        """Test optional field handling."""
        config = ValidatedMigrationConfig(
            target_root="/tmp/target",
            root_directory="/tmp/source",
            backup_root="/tmp/backup",
            target_extension=".converted.py",
        )

        assert config.target_root == "/tmp/target"
        assert config.root_directory == "/tmp/source"
        assert config.backup_root == "/tmp/backup"
        assert config.target_extension == ".converted.py"

    def test_config_class_settings(self):
        """Test pydantic Config class settings."""
        # Should allow assignment after creation
        config = ValidatedMigrationConfig()
        config.line_length = 150  # Should validate and allow
        assert config.line_length == 150

        # Should reject invalid assignment
        with pytest.raises(ValueError):
            config.line_length = 300  # Too high


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_validate_migration_config_valid(self):
        """Test validate_migration_config with valid config."""
        config_dict = {
            "line_length": 100,
            "file_patterns": ["test_*.py"],
            "dry_run": True,
        }

        result = validate_migration_config(config_dict)
        assert isinstance(result, ValidatedMigrationConfig)
        assert result.line_length == 100
        assert result.file_patterns == ["test_*.py"]
        assert result.dry_run is True

    def test_validate_migration_config_invalid(self):
        """Test validate_migration_config with invalid config."""
        config_dict = {
            "line_length": 50,  # Invalid - too low
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_migration_config(config_dict)

        assert "Invalid migration configuration" in str(exc_info.value)
        assert "configuration" in str(exc_info.value)

    def test_validate_migration_config_object_valid(self):
        """Test validate_migration_config_object with valid object."""

        # Create a mock config object
        class MockConfig:
            def __init__(self):
                self.line_length = 120
                self.file_patterns = ["test_*.py"]
                self.dry_run = False

        mock_config = MockConfig()
        result = validate_migration_config_object(mock_config)

        assert isinstance(result, ValidatedMigrationConfig)
        assert result.line_length == 120
        assert result.file_patterns == ["test_*.py"]
        assert result.dry_run is False

    def test_validate_migration_config_object_invalid(self):
        """Test validate_migration_config_object with invalid object."""

        class MockConfig:
            def __init__(self):
                self.line_length = 30  # Invalid - too low

        mock_config = MockConfig()

        with pytest.raises(ValidationError) as exc_info:
            validate_migration_config_object(mock_config)

        assert "Invalid migration configuration" in str(exc_info.value)

    def test_validate_migration_config_object_no_dict(self):
        """Test validate_migration_config_object with object without __dict__."""

        class SimpleObject:
            line_length = 120

        obj = SimpleObject()
        result = validate_migration_config_object(obj)

        assert isinstance(result, ValidatedMigrationConfig)
        assert result.line_length == 120

    def test_create_validated_config(self):
        """Test create_validated_config function."""
        result = create_validated_config(
            line_length=150,
            file_patterns=["custom_*.py"],
            dry_run=True,
        )

        assert isinstance(result, ValidatedMigrationConfig)
        assert result.line_length == 150
        assert result.file_patterns == ["custom_*.py"]
        assert result.dry_run is True

    def test_create_validated_config_invalid(self):
        """Test create_validated_config with invalid parameters."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            create_validated_config(line_length=40)  # Too low


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_none_values(self):
        """Test handling of None values."""
        config = ValidatedMigrationConfig(
            target_root=None,
            backup_root=None,
            target_extension=None,
        )

        assert config.target_root is None
        assert config.backup_root is None
        assert config.target_extension is None

    def test_empty_strings(self):
        """Test handling of empty strings where allowed."""
        config = ValidatedMigrationConfig(target_suffix="")
        assert config.target_suffix == ""

    def test_list_defaults(self):
        """Test list field defaults."""
        config = ValidatedMigrationConfig()
        assert config.file_patterns == ["test_*.py"]
        assert config.test_method_prefixes == ["test"]

    def test_field_descriptions(self):
        """Test that field descriptions are set correctly."""
        # This is more of a documentation test - ensuring descriptions exist
        schema = ValidatedMigrationConfig.model_json_schema()

        # Check some key fields have descriptions
        assert "description" in schema["properties"]["line_length"]
        assert "description" in schema["properties"]["file_patterns"]
        assert "description" in schema["properties"]["dry_run"]

    def test_config_json_schema(self):
        """Test that JSON schema generation works."""
        schema = ValidatedMigrationConfig.model_json_schema()

        assert "properties" in schema
        assert "line_length" in schema["properties"]
        assert "file_patterns" in schema["properties"]

        # Check constraints are present in the anyOf structure
        line_length_schema = schema["properties"]["line_length"]
        assert "anyOf" in line_length_schema
        # Find the constraint object in anyOf
        constraint_obj = None
        for item in line_length_schema["anyOf"]:
            if "minimum" in item and "maximum" in item:
                constraint_obj = item
                break
        assert constraint_obj is not None
        assert constraint_obj["minimum"] == 60
        assert constraint_obj["maximum"] == 200


class TestValidationErrorHandling:
    """Test comprehensive error handling."""

    def test_multiple_validation_errors(self):
        """Test handling multiple validation errors."""
        config_dict = {
            "line_length": 300,  # Too high
            "file_patterns": [],  # Empty
            "test_method_prefixes": ["", "   "],  # Invalid prefixes
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_migration_config(config_dict)

        error_str = str(exc_info.value)
        assert "Invalid migration configuration" in error_str

    def test_nested_validation_errors(self):
        """Test validation of nested/complex fields."""
        # Test with invalid nested list elements
        config_dict = {
            "file_patterns": ["valid_*.py", "", "another_valid_*.py"],
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_migration_config(config_dict)

        assert "Invalid file pattern" in str(exc_info.value)

    def test_type_validation_errors(self):
        """Test type validation errors."""
        from pydantic import ValidationError as PydanticValidationError

        # Valid type conversions should work
        config1 = ValidatedMigrationConfig(line_length="120")  # String to int
        assert config1.line_length == 120

        config2 = ValidatedMigrationConfig(dry_run="true")  # String to bool
        assert config2.dry_run is True

        # Invalid type conversions should fail
        with pytest.raises(PydanticValidationError):
            ValidatedMigrationConfig(file_patterns="test_*.py")  # String instead of list

        # Invalid boolean string should fail
        with pytest.raises(PydanticValidationError):
            ValidatedMigrationConfig(dry_run="not_boolean")

    def test_assignment_validation(self):
        """Test validation on field assignment."""
        config = ValidatedMigrationConfig()

        # Valid assignment
        config.line_length = 150
        assert config.line_length == 150

        # Invalid assignment
        with pytest.raises(ValueError):
            config.line_length = 250  # Too high

        with pytest.raises(ValueError):
            config.line_length = 40  # Too low


class TestConfigurationScenarios:
    """Test realistic configuration scenarios."""

    def test_minimal_config(self):
        """Test minimal valid configuration."""
        config = ValidatedMigrationConfig(
            file_patterns=["test_*.py"],
            test_method_prefixes=["test"],
        )

        assert config.file_patterns == ["test_*.py"]
        assert config.test_method_prefixes == ["test"]
        # Other fields should have defaults
        assert config.line_length == 120
        assert config.dry_run is False

    def test_full_config(self):
        """Test comprehensive configuration."""
        config = ValidatedMigrationConfig(
            target_root="/output",
            root_directory="/source",
            file_patterns=["test_*.py", "check_*.py"],
            recurse_directories=True,
            backup_originals=True,
            backup_root="/backup",
            target_suffix="_pytest",
            target_extension=".py",
            line_length=100,
            dry_run=False,
            fail_fast=True,
            test_method_prefixes=["test", "it"],
            parametrize=True,
            parametrize_ids=True,
            parametrize_type_hints=False,
            degradation_enabled=True,
            degradation_tier="advanced",
        )

        assert config.target_root == "/output"
        assert config.line_length == 100
        assert config.parametrize_ids is True
        assert config.degradation_tier == "advanced"

    def test_development_config(self):
        """Test configuration suitable for development."""
        config = ValidatedMigrationConfig(
            dry_run=True,
            fail_fast=False,
            degradation_enabled=False,
            line_length=88,  # Black default
        )

        assert config.dry_run is True
        assert config.fail_fast is False
        assert config.degradation_enabled is False
        assert config.line_length == 88

    def test_production_config(self):
        """Test configuration suitable for production."""
        config = ValidatedMigrationConfig(
            dry_run=False,
            fail_fast=True,
            backup_originals=True,
            degradation_enabled=True,
            degradation_tier="essential",
            line_length=120,
        )

        assert config.dry_run is False
        assert config.fail_fast is True
        assert config.backup_originals is True
        assert config.degradation_enabled is True
        assert config.degradation_tier == "essential"
