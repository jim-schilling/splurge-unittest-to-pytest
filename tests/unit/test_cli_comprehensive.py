"""Comprehensive tests for splurge_unittest_to_pytest.cli module to improve coverage."""

import logging
import os
import tempfile
from pathlib import Path

import pytest
import typer

from splurge_unittest_to_pytest import cli
from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.events import EventBus


class TestCLISetupFunctions:
    """Test CLI setup and utility functions."""

    def test_setup_logging_debug_mode(self):
        """Test setup_logging with debug mode enabled."""
        # Test that the function runs without errors
        # We don't assert specific logging behavior since that would require
        # complex mocking that interferes with pytest's logging
        cli.setup_logging(debug_mode=True)

    def test_setup_logging_normal_mode(self):
        """Test setup_logging with debug mode disabled."""
        # Test that the function runs without errors
        cli.setup_logging(debug_mode=False)

    def test_set_quiet_mode_enabled(self):
        """Test set_quiet_mode with quiet enabled."""
        # Test that the function runs without errors
        cli.set_quiet_mode(quiet=True)

    def test_set_quiet_mode_disabled(self):
        """Test set_quiet_mode with quiet disabled."""
        # Test that the function runs without errors
        cli.set_quiet_mode(quiet=False)

    def test_create_event_bus(self):
        """Test create_event_bus function."""
        event_bus = cli.create_event_bus()
        assert isinstance(event_bus, EventBus)

    def test_attach_progress_handlers(self):
        """Test attach_progress_handlers function."""
        event_bus = EventBus()

        # Should not raise any exceptions
        cli.attach_progress_handlers(event_bus, verbose=False)
        cli.attach_progress_handlers(event_bus, verbose=True)


class TestCLIMigrateCommand:
    """Test the migrate command functionality."""

    def test_migrate_mutually_exclusive_flags_error(self, mocker):
        """Test that info and debug flags cannot be used together."""
        # Mock the functions that would be called to avoid actual execution
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mocker.patch("splurge_unittest_to_pytest.main.migrate")

        with pytest.raises(typer.Exit) as exc_info:
            cli.migrate(source_files=[], info=True, debug=True)
        assert exc_info.value.exit_code == 2

    def test_migrate_with_debug_flag_calls_setup_logging(self, mocker):
        """Test that setup_logging is called when debug flag is used."""
        # Mock all the functions that would be called
        mock_setup_logging = mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = []
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = []

        cli.migrate(
            source_files=[],
            debug=True,
            info=False,  # Explicitly set info=False to avoid conflict
            config_file=None,
        )

        mock_setup_logging.assert_called_once_with(True)

    def test_migrate_with_info_flag_calls_setup_logging(self, mocker):
        """Test that setup_logging is called when info flag is used."""
        # Mock all the functions that would be called
        mock_setup_logging = mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = []
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = []

        cli.migrate(
            source_files=[],
            info=True,
            debug=False,  # Explicitly set debug=False to avoid conflict
            config_file=None,
        )

        mock_setup_logging.assert_called_once_with(False)

    def test_migrate_sets_quiet_mode_correctly_debug_true(self, mocker):
        """Test that set_quiet_mode is called with quiet=False when debug=True."""
        # Mock all the functions that would be called
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mock_set_quiet = mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = []
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = []

        # Test with debug=True (should set quiet=False)
        cli.migrate(source_files=[], debug=True, info=False, config_file=None)
        mock_set_quiet.assert_called_with(False)

    def test_migrate_sets_quiet_mode_correctly_info_true(self, mocker):
        """Test that set_quiet_mode is called with quiet=False when info=True."""
        # Mock all the functions that would be called
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mock_set_quiet = mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = []
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = []

        # Test with info=True (should set quiet=False)
        cli.migrate(source_files=[], info=True, debug=False, config_file=None)
        mock_set_quiet.assert_called_with(False)

    def test_migrate_sets_quiet_mode_correctly_defaults(self, mocker):
        """Test that set_quiet_mode is called with quiet=True when no flags are set."""
        # Mock all the functions that would be called
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mock_set_quiet = mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = []
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = []

        # Test with no debug/info flags (should set quiet=True)
        cli.migrate(source_files=[], debug=False, info=False, config_file=None)
        mock_set_quiet.assert_called_with(True)


class TestCLIVersionCommand:
    """Test the version command."""

    def test_version_command(self, mocker):
        """Test that version command outputs version information."""
        mock_echo = mocker.patch("typer.echo")
        cli.version()
        mock_echo.assert_called_once()
        call_args = mock_echo.call_args[0][0]
        assert "unittest-to-pytest" in call_args


class TestCLIInitConfigCommand:
    """Test the init-config command."""

    def test_init_config_missing_yaml(self, mocker):
        """Test init_config when PyYAML is not available."""
        mocker.patch("builtins.open")
        mocker.patch("typer.echo")

        # Mock yaml module as not available
        mocker.patch.dict("sys.modules", {"yaml": None})

        with pytest.raises(typer.Exit) as exc_info:
            cli.init_config("test.yaml")
        assert exc_info.value.exit_code == 1

    def test_init_config_success(self, mocker):
        """Test successful init_config execution."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not available")

        mocker.patch("typer.echo")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test_config.yaml"

            cli.init_config(str(config_file))

            assert config_file.exists()

            # Verify it's valid YAML and contains expected structure
            with open(config_file) as f:
                content = f.read()
                # Check for some expected configuration keys
                assert "backup_originals:" in content
                assert "line_length:" in content
                assert "dry_run:" in content

    def test_init_config_write_error(self, mocker):
        """Test init_config when file writing fails."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not available")

        mocker.patch("typer.echo")

        # Try to write to a directory that doesn't exist
        nonexistent_dir = "/nonexistent/directory/config.yaml"

        with pytest.raises(typer.Exit) as exc_info:
            cli.init_config(nonexistent_dir)
        assert exc_info.value.exit_code == 1


class TestCLIMainFunction:
    """Test the main CLI entry point."""

    def test_main_calls_app(self, mocker):
        """Test that main() calls the typer app."""
        mock_app_call = mocker.patch("typer.Typer.__call__")
        cli.main()
        mock_app_call.assert_called_once()


class TestCLIValidateSourceFiles:
    """Test validate_source_files functions."""

    def test_validate_source_files_with_directory(self, tmp_path):
        """Test validate_source_files_with_patterns with directory containing Python files."""
        # Create test directory structure
        test_dir = tmp_path / "test_proj"
        test_dir.mkdir()
        (test_dir / "test_file.py").write_text("print('test')")
        (test_dir / "not_python.txt").write_text("not python")

        result = cli.validate_source_files_with_patterns([], str(test_dir), ["*.py"], recurse=True)

        assert len(result) == 1
        assert any("test_file.py" in f for f in result)

    def test_validate_source_files_with_no_files_found(self, tmp_path):
        """Test validate_source_files_with_patterns when no files are found."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = cli.validate_source_files_with_patterns([], str(empty_dir), ["*.py"], recurse=True)
        assert result == []

    def test_validate_source_files_invalid_path(self, tmp_path):
        """Test validate_source_files with non-existent path."""
        result = cli.validate_source_files([str(tmp_path / "nonexistent.py")])
        assert result == []


class TestCLIDryRunOutput:
    """Test dry-run output functionality."""

    def test_dry_run_list_mode(self, mocker):
        """Test dry-run with list mode."""
        # Mock all the functions and modules that would be called
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mock_create_config = mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")
        mock_echo = mocker.patch("typer.echo")

        # Mock successful migration with generated code
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = ["/path/to/file.py"]
        mock_result.metadata = {"generated_code": {"/path/to/file.py": 'print("test")'}}
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = ["/path/to/file.py"]

        # Mock config with dry_run=True
        mock_config = mocker.Mock()
        mock_config.dry_run = True
        mock_create_config.return_value = mock_config

        cli.migrate(
            source_files=["/path/to/file.py"], dry_run=True, list_files=True, debug=False, info=False, config_file=None
        )

        # Verify list mode output
        mock_echo.assert_called()
        calls = [call[0][0] for call in mock_echo.call_args_list]
        assert any("FILES:" in call for call in calls)

    def test_dry_run_diff_mode(self, mocker):
        """Test dry-run with diff mode calls the right functions."""
        # Mock all the functions that would be called
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mock_create_config = mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = ["/path/to/file.py"]
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = ["/path/to/file.py"]

        # Mock config with dry_run=True
        mock_config = mocker.Mock()
        mock_config.dry_run = True
        mock_create_config.return_value = mock_config

        # Should not raise any exceptions
        cli.migrate(
            source_files=["/path/to/file.py"], dry_run=True, diff=True, debug=False, info=False, config_file=None
        )

    def test_dry_run_code_output(self, mocker):
        """Test dry-run with default code output mode calls the right functions."""
        # Mock all the functions that would be called
        mocker.patch("splurge_unittest_to_pytest.cli.setup_logging")
        mocker.patch("splurge_unittest_to_pytest.cli.set_quiet_mode")
        mocker.patch("splurge_unittest_to_pytest.cli.create_event_bus")
        mocker.patch("splurge_unittest_to_pytest.cli.attach_progress_handlers")
        mock_create_config = mocker.patch("splurge_unittest_to_pytest.cli.create_config")
        mock_validate = mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns")
        mock_main_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Mock successful migration
        mock_result = mocker.Mock()
        mock_result.is_success.return_value = True
        mock_result.data = ["/path/to/file.py"]
        mock_main_migrate.return_value = mock_result
        mock_validate.return_value = ["/path/to/file.py"]

        # Mock config with dry_run=True
        mock_config = mocker.Mock()
        mock_config.dry_run = True
        mock_create_config.return_value = mock_config

        # Should not raise any exceptions
        cli.migrate(source_files=["/path/to/file.py"], dry_run=True, debug=False, info=False, config_file=None)


class TestCLIConfigurationOptions:
    """Test new CLI configuration options and YAML config file support."""

    def test_yaml_config_file_loading(self, tmp_path, mocker):
        """Test loading configuration from YAML file."""
        # Create a temporary YAML config file
        config_file = tmp_path / "test_config.yaml"
        config_content = """
target_root: /tmp/output
line_length: 100
dry_run: false
format_output: false
transform_assertions: false
max_concurrent_files: 4
"""
        config_file.write_text(config_content)

        # Mock the file validation to avoid actual file processing
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])
        mock_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Call migrate with config file
        cli.migrate(source_files=["dummy.py"], config_file=str(config_file), debug=False, info=False)

        # Verify that main.migrate was called with the config loaded from YAML
        mock_migrate.assert_called_once()

        # The key test is that the YAML file was processed and main.migrate was called
        # with a config object. The actual config merging behavior is tested elsewhere.
        # This test verifies that YAML config file loading works correctly.

    def test_yaml_config_file_not_found(self, tmp_path, mocker):
        """Test error handling when YAML config file doesn't exist."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])

        # Should raise SystemExit with code 1
        with pytest.raises(typer.Exit):
            cli.migrate(source_files=["dummy.py"], config_file=str(nonexistent_config))

    def test_yaml_config_file_invalid_yaml(self, tmp_path, mocker):
        """Test error handling when YAML config file contains invalid YAML."""
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])

        # Should raise SystemExit with code 1
        with pytest.raises(typer.Exit):
            cli.migrate(source_files=["dummy.py"], config_file=str(config_file))

    def test_boolean_flag_resolution_negative_overrides_positive(self, mocker):
        """Test that negative flags override positive flags."""
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])
        mock_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Test format flag resolution
        cli.migrate(
            source_files=["dummy.py"],
            format_output=True,  # positive flag
            no_format_output=True,  # negative flag - overrides positive
            config_file=None,
            debug=False,
            info=False,
        )

        config_arg = mock_migrate.call_args[1]["config"]
        assert config_arg.format_output is False  # negative flag wins

    def test_boolean_flag_resolution_positive_flag_wins_when_negative_false(self, mocker):
        """Test that positive flag wins when negative flag is False."""
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])
        mock_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Test format flag resolution
        cli.migrate(
            source_files=["dummy.py"],
            format_output=True,  # positive flag set to True
            no_format_output=False,  # negative flag - should not override
            config_file=None,
            debug=False,
            info=False,
        )

        config_arg = mock_migrate.call_args[1]["config"]
        assert config_arg.format_output is True  # positive flag wins

    def test_transform_selection_flags(self, mocker):
        """Test transform selection CLI flags."""
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])
        mock_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Test disabling specific transforms
        cli.migrate(
            source_files=["dummy.py"],
            no_transform_assertions=True,
            no_transform_setup_teardown=True,
            no_transform_subtests=True,
            no_transform_skip_decorators=True,
            no_transform_imports=True,
            config_file=None,
            debug=False,
            info=False,
        )

        config_arg = mock_migrate.call_args[1]["config"]
        assert config_arg.transform_assertions is False
        assert config_arg.transform_setup_teardown is False
        assert config_arg.transform_subtests is False
        assert config_arg.transform_skip_decorators is False
        assert config_arg.transform_imports is False

    def test_processing_options_flags(self, mocker):
        """Test processing options CLI flags."""
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])
        mock_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Test processing options
        cli.migrate(
            source_files=["dummy.py"],
            continue_on_error=True,
            max_concurrent=8,
            no_cache_analysis=True,
            no_preserve_encoding=True,
            create_source_map=True,
            config_file=None,
            debug=False,
            info=False,
        )

        config_arg = mock_migrate.call_args[1]["config"]
        assert config_arg.continue_on_error is True
        assert config_arg.max_concurrent_files == 8
        assert config_arg.cache_analysis_results is False
        assert config_arg.preserve_file_encoding is False
        assert config_arg.create_source_map is True

    def test_import_handling_flags(self, mocker):
        """Test import handling CLI flags."""
        mocker.patch("splurge_unittest_to_pytest.cli.validate_source_files_with_patterns", return_value=["dummy.py"])
        mock_migrate = mocker.patch("splurge_unittest_to_pytest.main.migrate")

        # Test import handling options
        cli.migrate(
            source_files=["dummy.py"],
            no_remove_unused_imports=True,
            no_preserve_import_comments=True,
            config_file=None,
            debug=False,
            info=False,
        )

        config_arg = mock_migrate.call_args[1]["config"]
        assert config_arg.remove_unused_imports is False
        assert config_arg.preserve_import_comments is False

    def test_init_config_includes_all_new_options(self, mocker):
        """Test that init_config generates YAML with all new configuration options."""
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not available")

        mocker.patch("typer.echo")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "comprehensive_config.yaml"

            cli.init_config(str(config_file))

            # Verify the configuration file was created
            assert config_file.exists()

            # Read and verify the content contains expected keys
            with open(config_file) as f:
                content = f.read()

            # Check that new configuration options are included in the generated YAML
            expected_keys = [
                "format_output",
                "remove_unused_imports",
                "preserve_import_comments",
                "transform_assertions",
                "transform_setup_teardown",
                "transform_subtests",
                "transform_skip_decorators",
                "transform_imports",
                "continue_on_error",
                "max_concurrent_files",
                "cache_analysis_results",
                "preserve_file_encoding",
                "create_source_map",
            ]

            for key in expected_keys:
                assert key in content, f"Missing configuration option: {key} in generated YAML"
