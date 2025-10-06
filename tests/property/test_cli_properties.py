"""Property-based tests for CLI functionality.

This module contains Hypothesis-based property tests for the CLI
components in splurge_unittest_to_pytest, including argument parsing,
configuration building, and input validation.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from splurge_unittest_to_pytest.cli_adapters import build_config_from_cli
from splurge_unittest_to_pytest.context import MigrationConfig
from tests.hypothesis_config import DEFAULT_SETTINGS


# Strategy for generating valid file paths
@st.composite
def file_path_strategy(draw: st.DrawFn) -> str:
    """Generate valid file paths for testing."""
    # Generate a simple filename with valid characters
    filename = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"),
            min_size=1,
            max_size=20,
        )
    )
    # Ensure it ends with .py
    if not filename.endswith(".py"):
        filename += ".py"
    return filename


# Strategy for generating CLI argument dictionaries
@st.composite
def cli_args_strategy(draw: st.DrawFn) -> dict[str, Any]:
    """Generate realistic CLI argument combinations."""
    args = {}

    # File-related options
    args["source_files"] = draw(st.lists(file_path_strategy(), min_size=1, max_size=5))
    args["root_directory"] = draw(st.one_of(st.none(), file_path_strategy()))
    args["file_patterns"] = draw(
        st.lists(st.text(min_size=1, max_size=20).filter(lambda x: "*" in x or "?" in x), min_size=1, max_size=3)
    )
    args["recurse"] = draw(st.booleans())
    args["target_root"] = draw(st.one_of(st.none(), file_path_strategy()))

    # Processing options
    args["line_length"] = draw(st.integers(min_value=60, max_value=200))
    args["dry_run"] = draw(st.booleans())
    args["fail_fast"] = draw(st.booleans())
    args["continue_on_error"] = draw(st.booleans())
    args["max_concurrent"] = draw(st.integers(min_value=1, max_value=10))

    # Logging options
    args["verbose"] = draw(st.booleans())
    args["log_level"] = draw(st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"]))

    # Transformation options
    args["transform_assertions"] = draw(st.booleans())
    args["transform_setup_teardown"] = draw(st.booleans())
    args["transform_subtests"] = draw(st.booleans())
    args["transform_skip_decorators"] = draw(st.booleans())
    args["transform_imports"] = draw(st.booleans())

    # Import handling
    args["remove_unused_imports"] = draw(st.booleans())
    args["preserve_import_comments"] = draw(st.booleans())

    # Output options
    args["format_output"] = draw(st.booleans())
    args["suffix"] = draw(st.text(max_size=10))
    args["ext"] = draw(st.one_of(st.none(), st.text(min_size=1, max_size=5)))

    # Report options
    args["generate_report"] = draw(st.booleans())
    args["report_format"] = draw(st.sampled_from(["json", "yaml", "text"]))

    # Test configuration
    args["test_method_prefixes"] = draw(st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    args["assert_almost_equal_places"] = draw(st.integers(min_value=1, max_value=15))
    args["max_file_size_mb"] = draw(st.integers(min_value=1, max_value=50))

    return args


class TestCliProperties:
    """Property-based tests for CLI functionality."""

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_build_config_from_cli_produces_valid_config(self, cli_args: dict[str, Any]) -> None:
        """Test that build_config_from_cli always produces a valid MigrationConfig."""
        base_config = MigrationConfig()

        # Should not raise an exception
        result_config = build_config_from_cli(base_config, cli_args)

        # Should be a MigrationConfig instance
        assert isinstance(result_config, MigrationConfig)

        # Should have all expected attributes
        expected_attrs = [
            "line_length",
            "dry_run",
            "fail_fast",
            "verbose",
            "log_level",
            "transform_assertions",
            "transform_setup_teardown",
            "transform_subtests",
            "transform_skip_decorators",
            "transform_imports",
            "remove_unused_imports",
            "preserve_import_comments",
            "format_output",
            "generate_report",
            "test_method_prefixes",
            "assert_almost_equal_places",
            "max_file_size_mb",
        ]

        for attr in expected_attrs:
            assert hasattr(result_config, attr)

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_build_config_from_cli_preserves_base_config(self, cli_args: dict[str, Any]) -> None:
        """Test that build_config_from_cli preserves base config for unspecified options."""
        # Create a custom base config
        base_config = MigrationConfig(
            line_length=100, dry_run=True, transform_assertions=False, test_method_prefixes=["custom_prefix"]
        )

        result_config = build_config_from_cli(base_config, cli_args)

        # Options not in cli_args should preserve base values
        if "line_length" not in cli_args:
            assert result_config.line_length == 100
        if "dry_run" not in cli_args:
            assert result_config.dry_run
        if "transform_assertions" not in cli_args:
            assert not result_config.transform_assertions
        if "test_method_prefixes" not in cli_args:
            assert result_config.test_method_prefixes == ["custom_prefix"]

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_build_config_from_cli_overrides_base_config(self, cli_args: dict[str, Any]) -> None:
        """Test that build_config_from_cli properly overrides base config with CLI args."""
        base_config = MigrationConfig(line_length=80, dry_run=False)

        result_config = build_config_from_cli(base_config, cli_args)

        # CLI args should override base config
        if "line_length" in cli_args:
            assert result_config.line_length == cli_args["line_length"]
        if "dry_run" in cli_args:
            assert result_config.dry_run == cli_args["dry_run"]

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_build_config_from_cli_handles_invalid_args_gracefully(self, cli_args: dict[str, Any]) -> None:
        """Test that build_config_from_cli handles invalid arguments gracefully."""
        base_config = MigrationConfig()

        # Add some potentially invalid arguments
        invalid_args = cli_args.copy()
        invalid_args["invalid_field"] = "some_value"
        # Note: CLI adapter doesn't validate ranges, so we don't add invalid ranges

        # Should not raise an exception despite invalid args
        result_config = build_config_from_cli(base_config, invalid_args)

        # Should still produce a valid config
        assert isinstance(result_config, MigrationConfig)

        # Invalid fields should be ignored
        assert not hasattr(result_config, "invalid_field")

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_build_config_from_cli_is_deterministic(self, cli_args: dict[str, Any]) -> None:
        """Test that build_config_from_cli produces deterministic results."""
        base_config = MigrationConfig()

        # Same inputs should produce same outputs
        result1 = build_config_from_cli(base_config, cli_args)
        result2 = build_config_from_cli(base_config, cli_args)

        # Compare key attributes
        attrs_to_check = [
            "line_length",
            "dry_run",
            "fail_fast",
            "verbose",
            "log_level",
            "transform_assertions",
            "transform_setup_teardown",
            "transform_subtests",
            "remove_unused_imports",
            "format_output",
        ]

        for attr in attrs_to_check:
            assert getattr(result1, attr) == getattr(result2, attr)

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_cli_args_validation_preserves_semantics(self, cli_args: dict[str, Any]) -> None:
        """Test that CLI argument processing preserves expected semantics."""
        base_config = MigrationConfig()

        result_config = build_config_from_cli(base_config, cli_args)

        # Boolean flags should be preserved
        boolean_flags = [
            "dry_run",
            "fail_fast",
            "verbose",
            "transform_assertions",
            "transform_setup_teardown",
            "transform_subtests",
            "transform_skip_decorators",
            "transform_imports",
            "remove_unused_imports",
            "preserve_import_comments",
            "format_output",
            "generate_report",
        ]

        for flag in boolean_flags:
            if flag in cli_args:
                assert getattr(result_config, flag) == cli_args[flag]

        # Integer values should be within valid ranges
        if "line_length" in cli_args:
            assert 60 <= result_config.line_length <= 200
        if "assert_almost_equal_places" in cli_args:
            assert 1 <= result_config.assert_almost_equal_places <= 15
        if "max_file_size_mb" in cli_args:
            assert 1 <= result_config.max_file_size_mb <= 50
        if "max_concurrent" in cli_args:
            assert 1 <= result_config.max_concurrent_files <= 10

        # List values should be preserved
        if "test_method_prefixes" in cli_args:
            assert result_config.test_method_prefixes == cli_args["test_method_prefixes"]

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_cli_config_building_handles_edge_cases(self, cli_args: dict[str, Any]) -> None:
        """Test CLI config building with edge case inputs."""
        base_config = MigrationConfig()

        # Test with empty lists
        edge_args = cli_args.copy()
        edge_args["source_files"] = []
        edge_args["file_patterns"] = []
        edge_args["test_method_prefixes"] = []

        result_config = build_config_from_cli(base_config, edge_args)

        # Should handle empty collections gracefully
        assert isinstance(result_config, MigrationConfig)
        assert result_config.test_method_prefixes == []

    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    @given(cli_args=cli_args_strategy())
    def test_cli_config_transformation_flags_are_consistent(self, cli_args: dict[str, Any]) -> None:
        """Test that transformation flags work together consistently."""
        base_config = MigrationConfig()

        result_config = build_config_from_cli(base_config, cli_args)

        # If any transformation is enabled, we should have a valid config
        transform_flags = [
            result_config.transform_assertions,
            result_config.transform_setup_teardown,
            result_config.transform_subtests,
            result_config.transform_skip_decorators,
            result_config.transform_imports,
        ]

        # At least one transformation should be enabled by default or CLI
        assert any(transform_flags) or not any(
            cli_args.get(flag, False)
            for flag in [
                "transform_assertions",
                "transform_setup_teardown",
                "transform_subtests",
                "transform_skip_decorators",
                "transform_imports",
            ]
        )

        # Configuration should be self-consistent
        assert isinstance(result_config.line_length, int)
        assert isinstance(result_config.max_file_size_mb, int)
        assert isinstance(result_config.test_method_prefixes, list)
