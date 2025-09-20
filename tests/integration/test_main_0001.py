import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import cast

import libcst as cst
import pytest

from splurge_unittest_to_pytest.main import convert_file, convert_string, find_unittest_files


def _import_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError("could not create spec")
    module = importlib.util.module_from_spec(spec)
    original = sys.modules.get(module_name)
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original


def test_convert_and_import_all_data_files(tmp_path: Path) -> None:
    data_dir = Path(__file__).parents[2] / "tests" / "data"
    out_dir = tmp_path / "converted"
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in sorted(data_dir.glob("unittest_*.txt")):
        src = p.read_text(encoding="utf8")
        res = convert_string(src)
        code = getattr(res, "converted_code", None)
        assert code is not None, f"Conversion failed for {p}"
        out_file = out_dir / (p.stem + ".py")
        out_file.write_text(code, encoding="utf8")
        module_name = f"converted_{p.stem}"
        try:
            _import_from_path(module_name, out_file)
        except ModuleNotFoundError:
            continue
        except NameError:
            raise
        except Exception as exc:
            pytest.fail(f"Import failed for {p}: {exc!r}")


def test_converted_module_executes_and_autouse_attaches(tmp_path: Path) -> None:
    src = textwrap.dedent(
        "\n        import unittest\n        import tempfile\n\n        class TestFoo(unittest.TestCase):\n            def setUp(self) -> None:\n                self.tmp = 123\n\n            def test_using_tmp(self) -> None:\n                assert self.tmp == 123\n    "
    )
    res = convert_string(src)
    assert res.has_changes
    code = res.converted_code
    p = tmp_path / "converted.py"
    p.write_text(code, encoding="utf-8")
    compiled = compile(code, str(p), "exec")
    globals_dict: dict[str, object] = {}
    exec(compiled, globals_dict)
    if "TestFoo" in globals_dict:
        T = cast(type, globals_dict["TestFoo"])
        func = getattr(T, "test_using_tmp")
        params = getattr(func, "__code__", None)
        if params is not None:
            assert getattr(params, "co_argcount", 0) >= 1
        else:
            assert hasattr(T, "setUp")
    else:
        assert "test_using_tmp" in globals_dict
        func = globals_dict["test_using_tmp"]
        params = getattr(func, "__code__", None)
        assert params is not None and getattr(params, "co_argcount", 0) >= 1


def read_sample(n: int) -> str:
    p = Path(__file__).parents[1] / "data" / f"unittest_{n:02d}.txt"
    return p.read_text()


def test_pipeline_converts_sample_and_parses() -> None:
    src = read_sample(1)
    res = convert_string(src)
    assert res.converted_code
    cst.parse_module(res.converted_code)


def _write_converted(src_path: Path, out_dir: Path) -> Path:
    result = convert_file(str(src_path))
    assert result.has_changes
    out_path = out_dir / (src_path.stem + "_converted.py")
    out_path.write_text(result.converted_code, encoding="utf-8")
    return out_path


def test_convert_and_pytest_collection(tmp_path: Path) -> None:
    """Convert a couple of example unittest files and run pytest collection/execution on them."""
    data_dir = Path(__file__).parents[2] / "data"
    candidates = ["unittest_01.txt", "unittest_06.txt", "unittest_21.txt"]
    sample_files = [data_dir / name for name in candidates if (data_dir / name).exists()]
    if not sample_files:
        return
    out_dir = tmp_path / "converted"
    out_dir.mkdir()
    converted_paths = []
    for src in sample_files:
        converted_paths.append(_write_converted(src, out_dir))
    cmd = [sys.executable, "-m", "pytest", "-q", str(out_dir)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.returncode == 0, f"pytest failed on converted files:\n{proc.stdout}"


def test_convert_and_run_single_file(tmp_path: Path) -> None:
    src_path = Path(__file__).parents[1] / "data" / "unittest_01.txt"
    src = src_path.read_text()
    res = convert_string(src)
    assert res.converted_code
    out_file = tmp_path / "converted.py"
    out_file.write_text(res.converted_code)
    proc = subprocess.run(
        ["python", "-m", "pytest", "-q", str(out_file)], capture_output=True, text=True, cwd=str(tmp_path)
    )
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout


def test_convert_sample_backup(tmp_path: Path) -> None:
    sample = Path("tests/data/test_schema_parser.py.bak.1757364222")
    if not sample.exists():
        pytest.skip("sample backup not present")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = convert_file(sample, output_path=out_dir / sample.name)
    assert result.has_changes
    converted = out_dir / sample.name
    files = find_unittest_files(out_dir)
    assert converted in files or converted.exists()


def _run_converted_code(code: str, tmpdir: Path) -> None:
    p = tmpdir / "converted.py"
    p.write_text(code, encoding="utf-8")
    compile(code, str(p), "exec")


def test_smoke_convert_all_sample_unittest_files(tmp_path: Path) -> None:
    data_dir = Path(__file__).parent.parent / "data"
    files = sorted(data_dir.glob("unittest_*.txt"))
    assert files, "No sample unittest files found in tests/data"
    for f in files:
        src = f.read_text(encoding="utf-8")
        res = convert_string(src)
        assert res.has_changes
        code = res.converted_code
        td = tmp_path / f.stem
        td.mkdir()
        _run_converted_code(code, td)
