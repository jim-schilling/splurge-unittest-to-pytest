from pathlib import Path

from splurge_unittest_to_pytest.main import convert_string


def _run_converted_code(code: str, tmpdir: Path) -> None:
    p = tmpdir / "converted.py"
    p.write_text(code, encoding="utf-8")
    # Only compile the converted module to ensure it has no syntax errors.
    # We avoid executing the module to prevent import-time failures for
    # optional third-party packages used by examples (e.g., parameterized).
    compile(code, str(p), "exec")


def test_smoke_convert_all_sample_unittest_files(tmp_path: Path) -> None:
    data_dir = Path(__file__).parent.parent / "data"
    files = sorted(data_dir.glob("unittest_*.txt"))
    assert files, "No sample unittest files found in tests/data"
    for f in files:
        src = f.read_text(encoding="utf-8")
        res = convert_string(src, engine="pipeline")
        assert res.has_changes
        code = res.converted_code
        # run in a temp subdir to avoid import issues
        td = tmp_path / f.stem
        td.mkdir()
        _run_converted_code(code, td)
