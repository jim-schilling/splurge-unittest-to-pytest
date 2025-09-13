# type: ignore
from splurge_unittest_to_pytest import convert_string, convert_file
from splurge_unittest_to_pytest.main import is_unittest_file, find_unittest_files


def test_convert_string_no_changes(tmp_path) -> None:
    src = """import pytest\n\ndef test_ok():\n    assert True\n"""
    # convert_string should detect no changes for pytest files
    res = convert_string(src, engine="pipeline")
    assert not res.has_changes


def test_convert_file_reads_and_writes(tmp_path) -> None:
    p = tmp_path / "sample.py"
    p.write_text(
        """import unittest\n\nclass T(unittest.TestCase):\n    def test_x(self) -> None:\n        self.assertTrue(True)\n"""
    )

    res = convert_file(p, output_path=tmp_path / "out.py")
    assert res.has_changes
    assert (tmp_path / "out.py").exists()


def test_is_unittest_file_positive(tmp_path) -> None:
    p = tmp_path / "u.py"
    p.write_text("import unittest\nclass TestX(unittest.TestCase): pass\n")
    assert is_unittest_file(p)


def test_is_unittest_file_negative(tmp_path) -> None:
    p = tmp_path / "p.py"
    p.write_text("import pytest\ndef test_ok():\n    assert True\n")
    assert not is_unittest_file(p)


def test_find_unittest_files(tmp_path) -> None:
    d = tmp_path / "dir"
    d.mkdir()
    f1 = d / "a.py"
    f2 = d / "b.py"
    f1.write_text("import unittest\nclass TestA(unittest.TestCase): pass\n")
    f2.write_text("print('hi')\n")

    found = find_unittest_files(d)
    assert isinstance(found, list)
    assert any(str(p).endswith("a.py") for p in found)
