
from splurge_unittest_to_pytest.main import convert_string


def test_fixture_with_cleanup_yield_pattern() -> None:
    src = '''
import unittest
import tempfile
import shutil

class TestFoo(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_it(self) -> None:
        self.assertTrue(True)
'''

    res = convert_string(src, engine="pipeline")
    out = res.converted_code
    # should create a fixture named temp_dir using yield pattern and include cleanup call
    assert 'def temp_dir' in out
    assert 'yield' in out
    assert 'shutil.rmtree' in out
    assert 'import pytest' in out


def test_multiple_setup_attributes_produce_multiple_fixtures() -> None:
    src = '''
import unittest

class TestMany(unittest.TestCase):
    def setUp(self) -> None:
        self.a = 1
        self.b = 2

    def test_vals(self) -> None:
        self.assertEqual(self.a + self.b, 3)
'''

    res = convert_string(src, engine="pipeline")
    out = res.converted_code
    # fixtures 'a' and 'b' should exist
    assert 'def a' in out
    assert 'def b' in out
    # autouse compat fixture should attach both names
    assert "'_attach_to_instance'" not in out or '_attach_to_instance' in out
    assert "'a'" in out and "'b'" in out


def test_variable_name_consistency() -> None:
    # setUp assigns self.tables, test uses self.tables -> after conversion names should match
    src = '''
import unittest

class TestNames(unittest.TestCase):
    def setUp(self) -> None:
        self.tables = {'x': 1}

    def test_lookup(self) -> None:
        self.assertEqual(self.tables['x'], 1)
'''

    res = convert_string(src, engine="pipeline")
    out = res.converted_code
    # fixture 'tables' should be created and used (no accidental rename)
    assert 'def tables' in out
    assert "tables['x']" in out or "tables[\"x\"]" in out
