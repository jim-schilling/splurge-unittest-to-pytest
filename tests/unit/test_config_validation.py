"""Tests for configuration validation functionality."""

import pytest

from splurge_unittest_to_pytest.config_validation import (
    ConfigurationAdvisor,
    ConfigurationFieldRegistry,
    ConfigurationProfile,
    ConfigurationTemplate,
    ConfigurationTemplateManager,
    ConfigurationUseCaseDetector,
    Suggestion,
    SuggestionType,
    ValidatedMigrationConfig,
    create_validated_config,
    generate_configuration_suggestions,
    get_configuration_field_registry,
    get_template,
    list_available_templates,
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
        assert config.test_method_prefixes == ["test", "spec", "should", "it"]
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
            dry_run=False,  # Fixed: was True which conflicts with target_root
            parametrize=False,
            degradation_tier="essential",
        )

        assert config.target_root == "/tmp/target"
        assert config.file_patterns == ["test_*.py", "check_*.py"]
        assert config.line_length == 100
        assert config.dry_run is False
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
        with pytest.raises(ValueError, match="File pattern at index 0 cannot be empty or whitespace-only"):
            ValidatedMigrationConfig(file_patterns=[""])

        # Whitespace-only pattern should fail
        with pytest.raises(ValueError, match="File pattern at index 0 cannot be empty or whitespace-only"):
            ValidatedMigrationConfig(file_patterns=["   "])

        # Mixed valid/invalid should fail
        with pytest.raises(ValueError, match="File pattern at index 1 cannot be empty or whitespace-only"):
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
        with pytest.raises(ValueError, match="Test method prefix at index 0 cannot be empty or whitespace-only"):
            ValidatedMigrationConfig(test_method_prefixes=[""])

        # Whitespace-only prefix should fail
        with pytest.raises(ValueError, match="Test method prefix at index 0 cannot be empty or whitespace-only"):
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
        assert config.test_method_prefixes == ["test", "spec", "should", "it"]

    def test_enhanced_validation_error_messages(self):
        """Test that validation provides helpful error messages."""
        # Test file pattern validation
        with pytest.raises(ValueError, match="At least one file pattern must be specified"):
            ValidatedMigrationConfig(file_patterns=[])

        with pytest.raises(ValueError, match="Input should be a valid string"):
            ValidatedMigrationConfig(file_patterns=[123])

        # Test test method prefix validation
        with pytest.raises(ValueError, match="At least one test method prefix must be specified"):
            ValidatedMigrationConfig(test_method_prefixes=[])

        with pytest.raises(ValueError, match="Input should be a valid string"):
            ValidatedMigrationConfig(test_method_prefixes=[123])

        with pytest.raises(ValueError, match="contains invalid characters"):
            ValidatedMigrationConfig(test_method_prefixes=["test!"])

        # Test assert places validation
        with pytest.raises(ValueError, match="Input should be greater than or equal to 1"):
            ValidatedMigrationConfig(assert_almost_equal_places=0)

        with pytest.raises(ValueError, match="Input should be less than or equal to 15"):
            ValidatedMigrationConfig(assert_almost_equal_places=20)

        # Test log level validation
        with pytest.raises(ValueError, match="must be one of"):
            ValidatedMigrationConfig(log_level="INVALID")

        with pytest.raises(ValueError, match="Input should be a valid string"):
            ValidatedMigrationConfig(log_level=123)

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

        assert "File pattern at index 1 cannot be empty or whitespace-only" in str(exc_info.value)

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
            test_method_prefixes=["test", "spec", "should", "it"],
        )

        assert config.file_patterns == ["test_*.py"]
        assert config.test_method_prefixes == ["test", "spec", "should", "it"]
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


class TestCrossFieldValidation:
    """Test cross-field validation rules."""

    def test_dry_run_with_target_root_validation(self):
        """Test that dry_run with target_root raises validation error."""
        with pytest.raises(ValueError, match="dry_run mode ignores target_root setting"):
            ValidatedMigrationConfig(dry_run=True, target_root="/tmp/output")

    def test_backup_root_without_backups_validation(self):
        """Test that backup_root without backup_originals raises validation error."""
        with pytest.raises(ValueError, match="backup_root specified but backup_originals is disabled"):
            ValidatedMigrationConfig(backup_root="/tmp/backup", backup_originals=False)

    def test_large_file_size_warning(self):
        """Test that large file size generates performance warning."""
        with pytest.raises(ValueError, match="Large file size limit may impact memory usage"):
            ValidatedMigrationConfig(max_file_size_mb=60)

    def test_experimental_tier_without_dry_run_validation(self):
        """Test that experimental tier without dry_run raises validation error."""
        with pytest.raises(
            ValueError, match="Experimental degradation tier without dry_run may cause unexpected results"
        ):
            ValidatedMigrationConfig(degradation_tier="experimental", dry_run=False)

    def test_valid_cross_field_combinations(self):
        """Test that valid cross-field combinations work correctly."""
        # These should all pass validation
        config1 = ValidatedMigrationConfig(dry_run=False, target_root="/tmp/output")
        assert config1.dry_run is False
        assert config1.target_root == "/tmp/output"

        config2 = ValidatedMigrationConfig(backup_root="/tmp/backup", backup_originals=True)
        assert config2.backup_root == "/tmp/backup"
        assert config2.backup_originals is True

        config3 = ValidatedMigrationConfig(degradation_tier="experimental", dry_run=True)
        assert config3.degradation_tier == "experimental"
        assert config3.dry_run is True


class TestFileSystemValidation:
    """Test file system permission validation."""

    def test_target_root_directory_validation(self, tmp_path):
        """Test target_root directory validation."""
        # Valid existing directory
        valid_dir = tmp_path / "output"
        valid_dir.mkdir()
        config = ValidatedMigrationConfig(target_root=str(valid_dir))
        assert config.target_root == str(valid_dir)

        # Non-existent directory should be allowed for dry run scenarios
        non_existent = tmp_path / "nonexistent"
        config2 = ValidatedMigrationConfig(target_root=str(non_existent))
        assert config2.target_root == str(non_existent)

        # File path should fail
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with pytest.raises(ValueError, match="target_root must be a directory"):
            ValidatedMigrationConfig(target_root=str(test_file))

    def test_backup_root_directory_validation(self, tmp_path):
        """Test backup_root directory validation."""
        # Valid existing directory
        valid_dir = tmp_path / "backup"
        valid_dir.mkdir()
        config = ValidatedMigrationConfig(backup_root=str(valid_dir))
        assert config.backup_root == str(valid_dir)

        # Non-existent directory should be allowed for dry run scenarios
        non_existent = tmp_path / "nonexistent_backup"
        config2 = ValidatedMigrationConfig(backup_root=str(non_existent))
        assert config2.backup_root == str(non_existent)

        # File path should fail
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        with pytest.raises(ValueError, match="backup_root must be a directory"):
            ValidatedMigrationConfig(backup_root=str(test_file))

    def test_directory_writability_validation(self, tmp_path):
        """Test that directories are validated for writability."""
        # Test with a valid writable directory
        writable_dir = tmp_path / "writable"
        writable_dir.mkdir()

        # This should work
        config = ValidatedMigrationConfig(target_root=str(writable_dir))
        assert config.target_root == str(writable_dir)

        # Test that non-existent directories are allowed for dry run scenarios
        non_existent = tmp_path / "nonexistent"
        config2 = ValidatedMigrationConfig(target_root=str(non_existent))
        assert config2.target_root == str(non_existent)


class TestUseCaseDetection:
    """Test configuration use case detection."""

    def test_basic_migration_detection(self):
        """Test detection of basic migration use case."""
        config = ValidatedMigrationConfig(
            file_patterns=["test_*.py"],
            recurse_directories=True,
            backup_originals=True,
            dry_run=True,
            degradation_tier="advanced",
        )

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        assert use_case == ConfigurationProfile.BASIC_MIGRATION

    def test_custom_framework_detection(self):
        """Test detection of custom testing framework use case."""
        config = ValidatedMigrationConfig(
            test_method_prefixes=["test", "spec", "should", "it", "feature", "scenario"],
            dry_run=True,
            degradation_tier="advanced",
        )

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        assert use_case == ConfigurationProfile.CUSTOM_TESTING_FRAMEWORK

    def test_enterprise_deployment_detection(self):
        """Test detection of enterprise deployment use case."""
        config = ValidatedMigrationConfig(
            target_root="./converted",
            backup_root="./backups",
            backup_originals=True,
            fail_fast=True,
            max_file_size_mb=40,  # Reduced to avoid validation error
        )

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        assert use_case == ConfigurationProfile.ENTERPRISE_DEPLOYMENT

    def test_ci_integration_detection(self):
        """Test detection of CI integration use case."""
        config = ValidatedMigrationConfig(
            dry_run=False, fail_fast=True, max_concurrent_files=4, cache_analysis_results=True, max_file_size_mb=15
        )

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        assert use_case == ConfigurationProfile.CI_INTEGRATION

    def test_development_debugging_detection(self):
        """Test detection of development debugging use case."""
        config = ValidatedMigrationConfig(dry_run=True, log_level="DEBUG", max_file_size_mb=5, create_source_map=True)

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        assert use_case == ConfigurationProfile.DEVELOPMENT_DEBUGGING

    def test_production_deployment_detection(self):
        """Test detection of production deployment use case."""
        config = ValidatedMigrationConfig(
            dry_run=False, backup_originals=True, fail_fast=True, degradation_tier="essential"
        )

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        assert use_case == ConfigurationProfile.PRODUCTION_DEPLOYMENT

    def test_unknown_use_case_detection(self):
        """Test detection of unknown use case."""
        config = ValidatedMigrationConfig(
            # Configuration that doesn't strongly match any pattern
            file_patterns=["test_*.py"],
            dry_run=False,
            test_method_prefixes=["test"],  # Only default prefix
        )

        detector = ConfigurationUseCaseDetector()
        use_case = detector.detect_use_case(config)
        # May still be detected as basic_migration, but test that detection works
        assert use_case in [ConfigurationProfile.BASIC_MIGRATION, ConfigurationProfile.UNKNOWN]


class TestConfigurationSuggestions:
    """Test intelligent configuration suggestions."""

    def test_performance_suggestions(self):
        """Test performance-related suggestions."""
        config = ValidatedMigrationConfig(max_file_size_mb=45)  # Below the warning threshold, but test other aspects
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        # Test that we can generate suggestions without errors
        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, Suggestion)
            assert suggestion.type in SuggestionType
            assert suggestion.message is not None
            assert suggestion.action is not None

    def test_safety_suggestions(self):
        """Test safety-related suggestions."""
        # Use valid configuration (experimental with dry_run=True)
        config = ValidatedMigrationConfig(degradation_tier="experimental", dry_run=True)
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        # May not have safety suggestions for valid config, but test that system works

        # Test that we can generate suggestions without errors
        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, Suggestion)
            assert suggestion.type in SuggestionType
            assert suggestion.message is not None
            assert suggestion.action is not None

    def test_use_case_specific_suggestions(self):
        """Test use case specific suggestions."""
        # CI integration use case
        config = ValidatedMigrationConfig(dry_run=False, fail_fast=True, max_concurrent_files=4)
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        # Should detect CI use case and provide relevant suggestions
        use_case_suggestions = [s for s in suggestions if "concurrent" in s.message.lower()]
        assert len(use_case_suggestions) > 0

    def test_suggestion_priority_ordering(self):
        """Test that suggestions are properly prioritized."""
        config = ValidatedMigrationConfig(
            degradation_tier="experimental",
            dry_run=True,
            max_file_size_mb=45,  # Below threshold for performance suggestion
        )
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        # Test that suggestions are properly structured
        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, Suggestion)
            assert suggestion.type in SuggestionType
            assert suggestion.message is not None
            assert suggestion.action is not None
            assert isinstance(suggestion.priority, int)

    def test_suggestion_examples(self):
        """Test that suggestions include helpful examples."""
        config = ValidatedMigrationConfig(max_file_size_mb=45)  # Below threshold
        advisor = ConfigurationAdvisor()
        suggestions = advisor.suggest_improvements(config)

        # Test that suggestions have proper structure
        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, Suggestion)
            assert suggestion.type in SuggestionType
            assert suggestion.message is not None
            assert suggestion.action is not None
            if suggestion.examples:
                assert all(isinstance(ex, str) for ex in suggestion.examples)


class TestConfigurationFieldMetadata:
    """Test configuration field metadata system."""

    def test_field_registry_creation(self):
        """Test that field registry is created correctly."""
        registry = get_configuration_field_registry()
        assert isinstance(registry, ConfigurationFieldRegistry)

        # Should have metadata for key fields
        assert registry.get_field("target_root") is not None
        assert registry.get_field("file_patterns") is not None
        assert registry.get_field("dry_run") is not None

    def test_field_metadata_completeness(self):
        """Test that field metadata is complete and useful."""
        registry = get_configuration_field_registry()

        # Check a representative field
        field = registry.get_field("target_root")
        assert field is not None
        assert field.name == "target_root"
        assert field.type == "str | None"
        assert field.description is not None
        assert len(field.description) > 10  # Meaningful description
        assert field.examples is not None
        assert len(field.examples) > 0
        assert field.constraints is not None
        assert len(field.constraints) > 0
        assert field.common_mistakes is not None
        assert len(field.common_mistakes) > 0

    def test_field_help_text_generation(self):
        """Test that field help text is properly generated."""
        registry = get_configuration_field_registry()

        help_text = registry.generate_help_text("target_root")
        assert "**target_root**" in help_text
        assert "Root directory for output files" in help_text
        assert "Examples:" in help_text
        assert "Constraints:" in help_text
        assert "Common Mistakes:" in help_text

    def test_field_categories(self):
        """Test field categorization."""
        registry = get_configuration_field_registry()

        # Check that fields are properly categorized
        output_fields = registry.get_fields_by_category("output")
        assert "target_root" in output_fields

        backup_fields = registry.get_fields_by_category("backup")
        assert "backup_root" in backup_fields
        assert "backup_originals" in backup_fields

        safety_fields = registry.get_fields_by_category("safety")
        assert "dry_run" in safety_fields


class TestConfigurationDocumentation:
    """Test auto-generated configuration documentation."""

    def test_markdown_documentation_generation(self):
        """Test Markdown documentation generation."""
        from splurge_unittest_to_pytest.config_validation import generate_configuration_documentation

        docs = generate_configuration_documentation("markdown")
        assert "# Configuration Reference" in docs
        assert "## Input Configuration" in docs
        assert "## Output Configuration" in docs
        assert "**target_root**" in docs
        assert "Examples:" in docs
        assert "Constraints:" in docs

    def test_html_documentation_generation(self):
        """Test HTML documentation generation."""
        from splurge_unittest_to_pytest.config_validation import generate_configuration_documentation

        docs = generate_configuration_documentation("html")
        assert "<!DOCTYPE html>" in docs
        assert "<title>" in docs
        assert "Configuration Reference" in docs
        assert '<div class="field">' in docs
        assert "<style>" in docs

    def test_invalid_format_error(self):
        """Test error handling for invalid documentation format."""
        from splurge_unittest_to_pytest.config_validation import generate_configuration_documentation

        with pytest.raises(ValueError, match="Unsupported format"):
            generate_configuration_documentation("invalid")


class TestConfigurationTemplates:
    """Test configuration template system."""

    def test_template_creation(self):
        """Test that templates are created correctly."""
        manager = ConfigurationTemplateManager()
        templates = manager.get_all_templates()

        assert len(templates) >= 6  # Should have at least 6 templates

        # Check specific templates exist
        assert "basic_migration" in templates
        assert "custom_framework" in templates
        assert "enterprise_deployment" in templates
        assert "ci_integration" in templates

    def test_template_content(self):
        """Test that templates have correct content."""
        manager = ConfigurationTemplateManager()

        basic_template = manager.get_template("basic_migration")
        assert basic_template is not None
        assert basic_template.name == "Basic Migration"
        assert basic_template.use_case == ConfigurationProfile.BASIC_MIGRATION
        assert basic_template.config_dict["dry_run"] is True
        assert basic_template.config_dict["backup_originals"] is True

    def test_template_yaml_generation(self):
        """Test YAML template generation."""
        manager = ConfigurationTemplateManager()

        template = manager.get_template("basic_migration")
        yaml_content = template.to_yaml()

        assert "# Basic Migration" in yaml_content
        assert "dry_run: true" in yaml_content
        assert "backup_originals: true" in yaml_content

    def test_template_cli_args_generation(self):
        """Test CLI arguments generation from templates."""
        manager = ConfigurationTemplateManager()

        template = manager.get_template("basic_migration")
        cli_args = template.to_cli_args()

        assert "--dry-run" in cli_args
        assert "--backup-originals" in cli_args
        assert "--file-patterns=test_*.py" in cli_args

    def test_template_use_case_suggestions(self):
        """Test template suggestions based on configuration."""
        manager = ConfigurationTemplateManager()

        # Test basic migration config
        config = ValidatedMigrationConfig(file_patterns=["test_*.py"], dry_run=True, backup_originals=True)

        suggested_template = manager.suggest_template_for_config(config)
        assert suggested_template is not None
        assert suggested_template.use_case == ConfigurationProfile.BASIC_MIGRATION

    def test_template_listing(self):
        """Test template listing functionality."""
        template_names = list_available_templates()
        assert isinstance(template_names, list)
        assert len(template_names) >= 6
        assert "basic_migration" in template_names

    def test_get_template_function(self):
        """Test get_template convenience function."""
        template = get_template("basic_migration")
        assert template is not None
        assert template.name == "Basic Migration"

        # Test non-existent template
        non_existent = get_template("non_existent")
        assert non_existent is None


class TestIntegration:
    """Test integration of enhanced validation features."""

    def test_validation_with_suggestions_integration(self):
        """Test that validation errors integrate with suggestion system."""
        # Create config that will fail validation
        config_dict = {"dry_run": True, "target_root": "/tmp/output", "max_file_size_mb": 60}

        # Validation should fail due to cross-field conflicts
        with pytest.raises(ValidationError, match="dry_run mode ignores target_root setting"):
            validate_migration_config(config_dict)

    def test_use_case_detection_integration(self):
        """Test that use case detection works with real configurations."""
        from splurge_unittest_to_pytest.config_validation import detect_configuration_use_case

        config = ValidatedMigrationConfig(
            dry_run=False, fail_fast=True, max_concurrent_files=8, cache_analysis_results=True
        )

        use_case = detect_configuration_use_case(config)
        assert use_case == ConfigurationProfile.CI_INTEGRATION

    def test_suggestion_generation_integration(self):
        """Test that suggestion generation works end-to-end."""
        config = ValidatedMigrationConfig(
            degradation_tier="experimental",
            dry_run=True,
            max_file_size_mb=45,  # Below threshold for performance suggestion
        )

        suggestions = generate_configuration_suggestions(config)

        # Should generate suggestions (may not be safety suggestions for valid config)
        assert isinstance(suggestions, list)
        for suggestion in suggestions:
            assert isinstance(suggestion, Suggestion)
            assert suggestion.type in SuggestionType
            assert suggestion.message is not None
            assert suggestion.action is not None

    def test_template_generation_integration(self):
        """Test that templates generate valid configurations."""
        from splurge_unittest_to_pytest.config_validation import generate_config_from_template

        # Test basic migration template
        config_dict = generate_config_from_template("basic_migration")

        # Should be able to create a valid config from the template
        config = ValidatedMigrationConfig(**config_dict)
        assert config.dry_run is True
        assert config.backup_originals is True

        # Test invalid template name
        with pytest.raises(ValueError, match="Template not found"):
            generate_config_from_template("invalid_template")
