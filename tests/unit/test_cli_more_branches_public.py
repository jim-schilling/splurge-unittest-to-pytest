
from click.testing import CliRunner

from splurge_unittest_to_pytest.cli import main as cli_main
from splurge_unittest_to_pytest.main import ConversionResult
from splurge_unittest_to_pytest.exceptions import PermissionDeniedError, EncodingError


def test_backup_success_and_converted_verbose(monkeypatch, tmp_path):
    f = tmp_path / 'file.py'
    f.write_text('print(1)')
    backup_dir = tmp_path / 'bak'

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        return ConversionResult(original_code='a', converted_code='b', has_changes=True, errors=[])

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ['--backup', str(backup_dir), '--verbose', str(f)])
    assert result.exit_code == 0
    assert 'Backup created' in result.output
    assert 'Converted:' in result.output


def test_permission_denied_error_is_reported(monkeypatch, tmp_path):
    f = tmp_path / 'p.py'
    f.write_text('x')

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        raise PermissionDeniedError('no access')

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, [str(f)])
    assert result.exit_code == 1
    assert 'File access error' in result.output


def test_encoding_error_is_reported(monkeypatch, tmp_path):
    f = tmp_path / 'enc.py'
    f.write_text('y')

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        raise EncodingError('bad encoding')

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, [str(f)])
    assert result.exit_code == 1
    assert 'Encoding error' in result.output


def test_recursive_find_unittest_files_and_verbose(monkeypatch, tmp_path):
    d = tmp_path / 'dir'
    d.mkdir()
    f1 = d / 'a.py'
    f2 = d / 'b.py'
    f1.write_text('1')
    f2.write_text('2')

    # return both files as found
    monkeypatch.setattr('splurge_unittest_to_pytest.cli.find_unittest_files', lambda p: [f1, f2], raising=False)

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        return ConversionResult(original_code='a', converted_code='a', has_changes=False, errors=[])

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ['--recursive', '--verbose', str(d)])
    assert result.exit_code == 0
    assert 'Found 2 unittest files' in result.output


def test_output_path_passed_to_convert_file(monkeypatch, tmp_path):
    f = tmp_path / 'z.py'
    f.write_text('z')
    out_dir = tmp_path / 'out'
    out_dir.mkdir()

    captured = {}

    def fake_convert_file(file_path, output_path, encoding, autocreate, setup_patterns, teardown_patterns, test_patterns):
        captured['output_path'] = output_path
        return ConversionResult(original_code='a', converted_code='a', has_changes=False, errors=[])

    monkeypatch.setattr('splurge_unittest_to_pytest.cli.convert_file', fake_convert_file, raising=False)

    runner = CliRunner()
    result = runner.invoke(cli_main, ['--output', str(out_dir), str(f)])
    assert result.exit_code == 0
    assert captured['output_path'] == out_dir / f.name
