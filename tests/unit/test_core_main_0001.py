import pathlib
from splurge_unittest_to_pytest import main
from pathlib import Path
import pytest
from splurge_unittest_to_pytest import main as mod


def test_init_api_rhs_preserved():
    src = pathlib.Path(__file__).parent.parent / "data" / "test_init_api.py.txt"
    src_text = src.read_text(encoding="utf8")
    result = main.convert_string(src_text)
    out = result.converted_code if hasattr(result, "converted_code") else str(result)
    assert "yield _InitAPIData(str(sql_file), str(schema_file))" in out
    assert "def sql_file(init_api_data):" in out
    assert "return init_api_data.sql_file" in out
    assert "def schema_file(init_api_data):" in out
    assert "return init_api_data.schema_file" in out


def test_convert_string_syntax_error():
    src = "this is not valid python"
    res = mod.convert_string(src)
    assert res.has_changes is False
    assert res.original_code == src
    assert res.errors and "Failed to parse" in res.errors[0]


def test_convert_string_no_meaningful_changes(monkeypatch):
    src = "def foo():\n    return 1\n"

    def fake_run_pipeline(tree, *, autocreate=True):
        return tree

    monkeypatch.setattr(mod, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(mod, "has_meaningful_changes", lambda a, b: False)
    res = mod.convert_string(src)
    assert res.has_changes is False
    assert res.converted_code == src


def test_convert_file_file_not_found_raises():
    missing = Path("does-not-exist-12345.py")
    with pytest.raises(Exception) as excinfo:
        mod.convert_file(missing)
    assert excinfo.type in {mod.SplurgeFileNotFoundError, FileNotFoundError}


def test_convert_file_write_permission_error(tmp_path, monkeypatch):
    inp = tmp_path / "in.py"
    inp.write_text("def a():\n    pass\n")
    ConversionResult = mod.ConversionResult
    monkeypatch.setattr(
        mod,
        "convert_string",
        lambda *a, **k: ConversionResult(original_code="a", converted_code="b", has_changes=True, errors=[]),
    )
    out = tmp_path / "out.py"

    # Patch the atomic writer used by convert_file so we can simulate
    # permission errors without relying on a Path.write_text preflight.
    def fake_atomic_write(path, data, *, encoding=None):
        if Path(path) == out:
            raise PermissionError("nope")

    monkeypatch.setattr(mod, "atomic_write", fake_atomic_write)
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
    bad = d / "binfile.bin"
    with open(bad, "wb") as fh:
        fh.write(b"\xff\xff\xff")
    pc = d / "__pycache__"
    pc.mkdir()
    (pc / "ignored.py").write_text("import unittest")
    files = mod.find_unittest_files(d)
    assert any((p.name == "good.py" for p in files))
    assert mod.is_unittest_file(good)
    tmp = d / "pytest_file.py"
    tmp.write_text("import pytest\n")
    assert mod.is_unittest_file(tmp) is False


def test_convert_string_with_changes(monkeypatch):
    src = "def x():\n    return 1\n"
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
    monkeypatch.setattr(
        mod,
        "convert_string",
        lambda *a, **k: ConversionResult(original_code="o", converted_code="c", has_changes=True, errors=[]),
    )
    out = tmp_path / "out.py"
    res = mod.convert_file(inp, output_path=out)
    assert res.converted_code == "c"
    assert out.exists()


def test_is_unittest_file_permission_denied(tmp_path, monkeypatch):
    f = tmp_path / "f.py"
    f.write_text("print(1)")
    orig_exists = Path.exists

    def fake_exists(self):
        if self == f:
            raise PermissionError("nope")
        return orig_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    with pytest.raises(Exception) as excinfo:
        mod.is_unittest_file(f)
    assert excinfo.type in {mod.PermissionDeniedError, PermissionError}


def test_pattern_configurator_add_and_match():
    p = main.PatternConfigurator()
    assert p._is_setup_method("setUp")
    assert p._is_teardown_method("tearDown")
    assert p._is_test_method("test_something")
    p.add_setup_pattern("setupAll")
    assert p._is_setup_method("setupAllFeature")
    p.add_test_pattern("describe_")
    assert p._is_test_method("describe_feature")


def test_rewriter_ensures_self_with_fixture() -> None:
    src = "\nimport unittest\n\nclass TestDB(unittest.TestCase):\n    def setUp(self) -> None:\n        self.conn = setup_db()\n\n    def test_action(self) -> None:\n        self.assertTrue(True)\n"
    res = main.convert_string(src)
    assert "def test_action(conn" in res.converted_code
