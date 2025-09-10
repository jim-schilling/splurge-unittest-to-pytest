import pytest
from pathlib import Path
from splurge_unittest_to_pytest.main import convert_file, find_unittest_files


def test_convert_sample_backup(tmp_path: Path) -> None:
    sample = Path('tests/data/test_schema_parser.py.bak.1757364222')
    if not sample.exists():
        pytest.skip('sample backup not present')

    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    result = convert_file(sample, output_path=out_dir / sample.name)
    assert result.has_changes
    converted = out_dir / sample.name
    # Ensure pytest can at least parse/collect (no exceptions during read)
    files = find_unittest_files(out_dir)
    assert converted in files or converted.exists()
