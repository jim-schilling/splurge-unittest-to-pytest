from pathlib import Path


from splurge_unittest_to_pytest.main import convert_string, find_unittest_files


def test_pytest_import_inserted_before_fixtures() -> None:
    src = """
class TestX(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = 1
    def test_one(self) -> None:
        self.assertEqual(self.tmp, 1)
"""
    result = convert_string(src, engine="pipeline")
    assert result.has_changes
    out = result.converted_code
    # Ensure 'import pytest' appears before any '@pytest.fixture' decorator
    idx_import = out.find("import pytest")
    idx_deco = out.find("@pytest.fixture")
    assert idx_import != -1 and idx_deco != -1 and idx_import < idx_deco


def test_find_unittest_files_skips_pycache(tmp_path: Path) -> None:
    # Create a fake __pycache__ and a binary file inside
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    pycache = pkg / "__pycache__"
    pycache.mkdir()
    bin_file = pycache / "junk.pyc"
    bin_file.write_bytes(b"\x00\x01\x02\x03")

    # create a normal unittest file outside pycache
    test_file = pkg / "test_sample.py"
    test_file.write_text(
        "import unittest\nclass TestA(unittest.TestCase):\n    def test_x(self) -> None:\n        pass\n"
    )

    found = find_unittest_files(tmp_path)
    # Should find only the visible test_file, not the pyc
    assert test_file in found
    assert bin_file not in found
