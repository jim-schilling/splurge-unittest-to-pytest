import pytest

from splurge_unittest_to_pytest.cli_adapters import _unwrap_option, build_config_from_cli
from splurge_unittest_to_pytest.context import MigrationConfig


class TestUnwrapOption:
    """Test the _unwrap_option helper function."""

    def test_unwrap_option_with_default_attribute(self):
        """Test unwrapping an object with a default attribute."""

        class OptionLike:
            def __init__(self, default_value):
                self.default = default_value

        option = OptionLike("test_value")
        result = _unwrap_option(option)
        assert result == "test_value"

    def test_unwrap_option_without_default_attribute(self):
        """Test unwrapping an object without a default attribute."""
        regular_value = "plain_string"
        result = _unwrap_option(regular_value)
        assert result == "plain_string"

    def test_unwrap_option_with_exception_in_default(self):
        """Test unwrapping when accessing default raises an exception."""

        class BadOption:
            @property
            def default(self):
                raise RuntimeError("Cannot access default")

        bad_option = BadOption()
        # The _unwrap_option should propagate the exception from accessing default
        with pytest.raises(RuntimeError, match="Cannot access default"):
            _unwrap_option(bad_option)


class TestBuildConfigFromCli:
    """Test the build_config_from_cli function with various scenarios."""

    def test_boolean_coercion_comprehensive(self):
        """Test boolean coercion for all boolean fields."""
        base = MigrationConfig()

        # Test all boolean fields with various input types
        boolean_fields = {
            "dry_run": True,
            "fail_fast": False,
            "backup_originals": 0,  # Number 0 becomes False
            "format_output": 1,  # Number 1 becomes True
            "remove_unused_imports": 0,
            "preserve_import_comments": 1,
            "transform_assertions": True,
            "transform_setup_teardown": False,
            "transform_subtests": 1,
            "transform_skip_decorators": 0,
            "transform_imports": True,
            "continue_on_error": False,
            "cache_analysis_results": 1,
            "preserve_file_encoding": 0,
            "create_source_map": 1,
        }

        cfg = build_config_from_cli(base, boolean_fields)

        # Verify all boolean coercions worked
        assert cfg.dry_run is True
        assert cfg.fail_fast is False
        assert cfg.backup_originals is False  # 0 becomes False
        assert cfg.format_output is True
        assert cfg.remove_unused_imports is False
        assert cfg.preserve_import_comments is True  # 1 becomes True
        assert cfg.transform_assertions is True
        assert cfg.transform_setup_teardown is False
        assert cfg.transform_subtests is True
        assert cfg.transform_skip_decorators is False
        assert cfg.transform_imports is True
        assert cfg.continue_on_error is False
        assert cfg.cache_analysis_results is True
        assert cfg.preserve_file_encoding is False
        assert cfg.create_source_map is True

    def test_integer_coercion_edge_cases(self):
        """Test integer coercion with edge cases."""
        base = MigrationConfig()

        # Test valid integer conversions
        cfg = build_config_from_cli(
            base,
            {
                "max_file_size_mb": "42",
                "max_concurrent_files": 10,
                "assert_almost_equal_places": "7",
                "max_depth": 5,
            },
        )

        assert cfg.max_file_size_mb == 42
        assert cfg.max_concurrent_files == 10
        assert cfg.assert_almost_equal_places == 7
        assert cfg.max_depth == 5

    def test_list_coercion_comprehensive(self):
        """Test list coercion for file_patterns and test_method_prefixes."""
        base = MigrationConfig()

        # Test file_patterns with various inputs
        cfg1 = build_config_from_cli(base, {"file_patterns": "test_*.py,helper_*.py"})
        assert cfg1.file_patterns == ["test_*.py", "helper_*.py"]

        cfg2 = build_config_from_cli(base, {"file_patterns": ["a.py", "b.py"]})
        assert cfg2.file_patterns == ["a.py", "b.py"]

        cfg3 = build_config_from_cli(base, {"file_patterns": ("x.py", "y.py")})
        assert cfg3.file_patterns == ["x.py", "y.py"]

        # Test test_method_prefixes
        cfg4 = build_config_from_cli(base, {"test_method_prefixes": "test_,check_"})
        assert cfg4.test_method_prefixes == ["test_", "check_"]

    def test_mixed_field_types(self):
        """Test configuration with mixed field types."""
        base = MigrationConfig()

        mixed_config = {
            "max_file_size_mb": "100",
            "dry_run": True,
            "file_patterns": "test_*.py,integration_*.py",
            "backup_originals": 0,  # False
            "max_concurrent_files": 8,
            "transform_assertions": 1,  # True
            "test_method_prefixes": ["test_", "it_"],
        }

        cfg = build_config_from_cli(base, mixed_config)

        # Verify all types are correctly coerced
        assert cfg.max_file_size_mb == 100
        assert cfg.dry_run is True
        assert cfg.file_patterns == ["test_*.py", "integration_*.py"]
        assert cfg.backup_originals is False  # 0 becomes False
        assert cfg.max_concurrent_files == 8
        assert cfg.transform_assertions is True  # 1 becomes True
        assert cfg.test_method_prefixes == ["test_", "it_"]

    def test_empty_and_whitespace_list_handling(self):
        """Test handling of empty and whitespace-only list inputs."""
        base = MigrationConfig()

        # Empty string should result in empty list
        cfg1 = build_config_from_cli(base, {"file_patterns": ""})
        assert cfg1.file_patterns == []

        # Whitespace-only string should result in empty list
        cfg2 = build_config_from_cli(base, {"file_patterns": "   "})
        assert cfg2.file_patterns == []

        # Mixed empty entries should be filtered
        cfg3 = build_config_from_cli(base, {"file_patterns": "a.py,,b.py,   "})
        assert cfg3.file_patterns == ["a.py", "b.py"]

    def test_string_fields_passthrough(self):
        """Test that string fields are passed through unchanged."""
        base = MigrationConfig()

        string_config = {
            "backup_root": "/tmp/backup",
            "log_level": "DEBUG",
            "report_format": "json",
        }

        cfg = build_config_from_cli(base, string_config)

        assert cfg.backup_root == "/tmp/backup"
        assert cfg.log_level == "DEBUG"
        assert cfg.report_format == "json"

    def test_none_values_skip_override(self):
        """Test that None values do not override existing configuration."""
        base = MigrationConfig(max_file_size_mb=50, dry_run=True, file_patterns=["existing.py"])

        # None values should not change existing values
        cfg = build_config_from_cli(
            base,
            {
                "max_file_size_mb": None,
                "dry_run": None,
                "file_patterns": None,
            },
        )

        assert cfg.max_file_size_mb == 50
        assert cfg.dry_run is True
        assert cfg.file_patterns == ["existing.py"]

    def test_unknown_fields_are_ignored(self):
        """Test that unknown fields are completely ignored."""
        base = MigrationConfig(max_file_size_mb=25)

        cfg = build_config_from_cli(
            base,
            {
                "max_file_size_mb": "30",  # Known field
                "unknown_field": "ignored",
                "another_unknown": 123,
                "cli_specific_option": True,
            },
        )

        # Known field should be updated
        assert cfg.max_file_size_mb == 30

        # Unknown fields should not affect the config object
        # (We can't easily test that they were ignored, but we can verify
        # that the config is still valid and only known fields were processed)

    def test_option_stub_unwrapping(self):
        """Test that OptionStub objects are properly unwrapped."""

        class OptionStub:
            def __init__(self, default):
                self.default = default

        base = MigrationConfig()

        cfg = build_config_from_cli(
            base,
            {
                "max_file_size_mb": OptionStub("25"),
                "dry_run": OptionStub(True),
                "file_patterns": OptionStub("a.py,b.py"),
            },
        )

        assert cfg.max_file_size_mb == 25
        assert cfg.dry_run is True
        assert cfg.file_patterns == ["a.py", "b.py"]

    @pytest.mark.parametrize("invalid_value", ["not-a-number", "12.5", "", "abc"])
    def test_invalid_integer_raises_value_error(self, invalid_value):
        """Test that invalid integer values raise ValueError."""
        base = MigrationConfig()

        with pytest.raises(ValueError, match="Configuration value for max_file_size_mb must be an integer"):
            build_config_from_cli(base, {"max_file_size_mb": invalid_value})

    def test_config_validation_is_deferred(self):
        """Test that configuration validation happens at the MigrationConfig level."""
        base = MigrationConfig()

        # This should not raise an error in build_config_from_cli
        # (validation is deferred to MigrationConfig.with_override)
        cfg = build_config_from_cli(
            base,
            {
                "max_file_size_mb": "100",  # Valid value
            },
        )

        # The config should be created successfully
        assert cfg.max_file_size_mb == 100
        assert isinstance(cfg, MigrationConfig)
