from pathlib import Path


from splurge_unittest_to_pytest.main import find_unittest_files, convert_string


def test_find_unittest_files_skips_pycache(tmp_path: Path) -> None:
    # Create a regular unittest file
    a = tmp_path / "test_a.py"
    a.write_text("import unittest\nclass TestA(unittest.TestCase): pass")

    # Create a __pycache__ entry that contains a file which would otherwise match
    pc = tmp_path / "__pycache__"
    pc.mkdir()
    b = pc / "test_b.py"
    b.write_text("import unittest\nclass TestB(unittest.TestCase): pass")

    found = find_unittest_files(tmp_path)
    names = {p.name for p in found}
    assert "test_a.py" in names
    assert "test_b.py" not in names


def test_find_unittest_files_skips_unreadable(tmp_path: Path, monkeypatch) -> None:
    f = tmp_path / "test_unreadable.py"
    f.write_text("import unittest\nclass Test(unittest.TestCase): pass")

    # Monkeypatch Path.read_text to raise UnicodeDecodeError for this file only
    original_read = Path.read_text

    def fake_read(self, encoding="utf-8"):
        if self == f:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
        return original_read(self, encoding=encoding)

    monkeypatch.setattr(Path, "read_text", fake_read)

    found = find_unittest_files(tmp_path)
    # Should not raise and the unreadable file should be skipped
    assert all(p.name != "test_unreadable.py" for p in found)


def test_converter_emits_pytest_import_and_autouse_fixture() -> None:
    # Input simulates a unittest TestCase with setUp assigning temp_dir
    src = """
import unittest
import tempfile
import shutil

class TestExample(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_something(self):
        self.assertTrue(True)
"""

    res = convert_string(src, engine="pipeline")
    assert res.has_changes
    out = res.converted_code
    # pytest import should be present
    assert "import pytest" in out
    # autouse fixture attaching to instance should be present
    assert "_attach_to_instance" in out
    # fixture name temp_dir should be referenced as a function/param
    assert "def temp_dir(" in out or "def temp_dir" in out
