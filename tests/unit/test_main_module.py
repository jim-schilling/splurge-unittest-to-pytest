from pathlib import Path

import pytest

from splurge_unittest_to_pytest import main as mod


def test_convert_string_syntax_error():
    src = "this is not valid python"
    res = mod.convert_string(src)
    assert res.has_changes is False
    assert res.original_code == src
    assert res.errors and "Failed to parse" in res.errors[0]


def test_convert_string_no_meaningful_changes(monkeypatch):
    # Provide a valid Python module and stub run_pipeline + change detector
    src = "def foo():\n    return 1\n"

    def fake_run_pipeline(tree, autocreate=True):
        # return the same module back
        return tree

    monkeypatch.setattr(mod, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(mod, "has_meaningful_changes", lambda a, b: False)

    res = mod.convert_string(src)
    assert res.has_changes is False
    assert res.converted_code == src


def test_convert_file_file_not_found_raises():
    # Non-existent input -> project-specific FileNotFoundError
    missing = Path("does-not-exist-12345.py")
    with pytest.raises(Exception) as excinfo:
        mod.convert_file(missing)
    # ensure it's our mapped error class (imported into module namespace)
    assert excinfo.type in {mod.SplurgeFileNotFoundError, FileNotFoundError}


def test_convert_file_write_permission_error(tmp_path, monkeypatch):
    # Create a valid input file
    inp = tmp_path / "in.py"
    inp.write_text("def a():\n    pass\n")

    # Stub convert_string to say there are changes
    ConversionResult = mod.ConversionResult
    monkeypatch.setattr(
        mod,
        "convert_string",
        lambda *a, **k: ConversionResult(original_code="a", converted_code="b", has_changes=True, errors=[]),
    )

    # Make write_text raise PermissionError for the output path
    out = tmp_path / "out.py"
    orig_write = Path.write_text

    def fake_write(self, *args, **kwargs):
        if self == out:
            raise PermissionError("nope")
        return orig_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fake_write)

    with pytest.raises(Exception) as excinfo:
        mod.convert_file(inp, output_path=out)
    assert excinfo.type in {mod.PermissionDeniedError, PermissionError}


def test_pattern_configurator_basic():
    pc = mod.PatternConfigurator()
    before = pc.setup_patterns
    pc.add_setup_pattern("my_setup")
    assert "my_setup" in pc.setup_patterns and before != pc.setup_patterns
    assert pc._is_setup_method("setUp")
    assert pc._is_test_method("test_something")


def test_is_unittest_file_and_find_unittest_files(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    good = d / "good.py"
    good.write_text("import unittest\nclass TestX(unittest.TestCase):\n    pass\n")

    # Binary file that will raise UnicodeDecodeError when read as utf-8
    bad = d / "binfile.bin"
    with open(bad, "wb") as fh:
        fh.write(b"\xff\xff\xff")

    # __pycache__ should be ignored
    pc = d / "__pycache__"
    pc.mkdir()
    (pc / "ignored.py").write_text("import unittest")

    files = mod.find_unittest_files(d)
    assert any(p.name == "good.py" for p in files)
    # is_unittest_file returns True for good, False for pytest imports
    assert mod.is_unittest_file(good)
    tmp = d / "pytest_file.py"
    tmp.write_text("import pytest\n")
    assert mod.is_unittest_file(tmp) is False


def test_convert_string_with_changes(monkeypatch):
    src = "def x():\n    return 1\n"
    # fake run_pipeline returns a modified module
    converted = __import__("libcst").parse_module("def x():\n    return 2\n")

    monkeypatch.setattr(mod, "run_pipeline", lambda tree, autocreate=True: converted)
    monkeypatch.setattr(mod, "has_meaningful_changes", lambda a, b: True)

    res = mod.convert_string(src)
    assert res.has_changes is True
    assert res.converted_code == converted.code


def test_convert_file_success_write(tmp_path, monkeypatch):
    inp = tmp_path / "in.py"
    inp.write_text("def a():\n    pass\n")

    ConversionResult = mod.ConversionResult
    # Simulate convert_string returning changes
    monkeypatch.setattr(
        mod,
        "convert_string",
        lambda *a, **k: ConversionResult(original_code="o", converted_code="c", has_changes=True, errors=[]),
    )

    out = tmp_path / "out.py"
    res = mod.convert_file(inp, output_path=out)
    # After successful write, returned result should match our ConversionResult
    assert res.converted_code == "c"
    assert out.exists()


def test_is_unittest_file_permission_denied(tmp_path, monkeypatch):
    f = tmp_path / "f.py"
    f.write_text("print(1)")

    # Cause Path.exists to raise PermissionError
    orig_exists = Path.exists

    def fake_exists(self):
        if self == f:
            raise PermissionError("nope")
        return orig_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    with pytest.raises(Exception) as excinfo:
        mod.is_unittest_file(f)
    assert excinfo.type in {mod.PermissionDeniedError, PermissionError}
