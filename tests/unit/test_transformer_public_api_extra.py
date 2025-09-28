import pytest

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def make(code: str) -> str:
    return UnittestToPytestCstTransformer().transform_code(code)


def test_transformer_various_assertions():
    code = """
import unittest
class T(unittest.TestCase):
    def test_all(self):
        self.assertIsNone(None)
        self.assertIsNotNone(1)
        self.assertNotIn(3, [1,2])
        self.assertIs(1, 1)
        self.assertIsNot(1, 2)
        self.assertCountEqual([1,2],[2,1])
        self.assertRegex("abc", "a.")
        self.assertNotRegex("abc", "z+")
"""
    out = make(code)
    assert "assert None is None" in out or "is None" in out
    assert "is not None" in out
    assert "not in" in out
    assert " is " in out
    assert " is not " in out
    assert "==" in out  # count equal becomes equality under string-based approach
    assert "pytest" in out


def test_transformer_setUpClass_tearDownClass_transforms_to_fixture():
    code = """
import unittest
class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = 1
    @classmethod
    def tearDownClass(cls):
        cls.x = None
    def test_a(self):
        self.assertTrue(True)
"""
    out = make(code)
    assert "import pytest" in out
    assert "@pytest.fixture" in out
    assert "yield" in out


def test_transformer_does_not_duplicate_pytest_import():
    code = """
import pytest
import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertEqual(1,1)
"""
    out = make(code)
    assert out.count("import pytest") == 1


def test_transformer_no_unittest_still_returns_string():
    code = """
class A:
    pass
"""
    out = make(code)
    assert isinstance(out, str)
