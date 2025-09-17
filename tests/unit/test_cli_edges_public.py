import importlib
import logging

from click.testing import CliRunner

from splurge_unittest_to_pytest import cli as cli_module
from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.main import ConversionResult
from splurge_unittest_to_pytest.exceptions import SplurgeError


def test_reload_sets_diagnostics_logger(monkeypatch):
    monkeypatch.setenv('SPLURGE_ENABLE_DIAGNOSTICS', '1')
    monkeypatch.setenv('SPLURGE_DIAGNOSTICS_VERBOSE', '1')

    # reload the module so top-level diagnostics wiring runs
    importlib.reload(cli_module)

    diag_logger = getattr(cli_module, 'diag_logger', None)
    assert diag_logger is not None
    assert isinstance(diag_logger.level, int)
    # verbose env should set DEBUG
    assert diag_logger.level == logging.DEBUG


def test_verbose_dry_run_shows_all_diff_summary_branches(monkeypatch, tmp_path):
    f = tmp_path / 's.py'
    original = 'class X(unittest.TestCase):\n    def test(self):\n        self.assertTrue(True)\n'
    converted = 'import pytest\nclass X:\n    def test(self):\n        assert True\n'
    f.write_text(original)

    def fake_convert_string(src, autocreate=True, pattern_config=None):
        return ConversionResult(original_code=original, converted_code=converted, has_changes=True, errors=[])

    monkeypatch.setattr('splurge_unittest_to_pytest.main.convert_string', fake_convert_string, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ['--dry-run', '--verbose', str(f)])
    assert result.exit_code == 0
    out = result.output
    assert 'Would convert' in out
    assert 'Unittest assertions converted' in out
    assert 'Pytest assertions created' in out or 'Lines changed' in out
    assert 'Removed unittest.TestCase inheritance' in out
    assert 'Added pytest import' in out


def test_splurge_error_is_caught_and_reports(monkeypatch, tmp_path):
    f = tmp_path / 'se.py'
    f.write_text('x')

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        raise SplurgeError('boom')

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, [str(f)])
    assert result.exit_code == 1
    assert 'Error processing' in result.output


def test_unexpected_exception_is_reported(monkeypatch, tmp_path):
    f = tmp_path / 'u.py'
    f.write_text('y')

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        raise RuntimeError('unexpected')

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, [str(f)])
    assert result.exit_code == 1
    assert 'Unexpected error processing' in result.output


def test_convert_file_errors_printed_and_exit(monkeypatch, tmp_path):
    f = tmp_path / 'err.py'
    f.write_text('z')

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        return ConversionResult(original_code='a', converted_code='b', has_changes=False, errors=['bad parse'])

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, [str(f)])
    assert result.exit_code == 1
    assert 'files had errors' in result.output or 'Error in' in result.output
