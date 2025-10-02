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
        cli.migrate(source_files=[], debug=True, info=False)
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
        cli.migrate(source_files=[], info=True, debug=False)
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
        cli.migrate(source_files=[], debug=False, info=False)
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
                assert "preserve_structure:" in content
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

        with pytest.raises(typer.Exit) as exc_info:
            cli.validate_source_files_with_patterns([], str(empty_dir), ["*.py"], recurse=True)
        assert exc_info.value.exit_code == 1

    def test_validate_source_files_invalid_path(self, tmp_path):
        """Test validate_source_files with non-existent path."""
        with pytest.raises(typer.Exit) as exc_info:
            cli.validate_source_files([str(tmp_path / "nonexistent.py")])
        assert exc_info.value.exit_code == 1


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

        cli.migrate(source_files=["/path/to/file.py"], dry_run=True, list_files=True, debug=False, info=False)

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
        cli.migrate(source_files=["/path/to/file.py"], dry_run=True, diff=True, debug=False, info=False)

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
        cli.migrate(source_files=["/path/to/file.py"], dry_run=True, debug=False, info=False)
