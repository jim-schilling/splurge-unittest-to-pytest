import pytest

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def make(code: str) -> str:
    return UnittestToPytestCstTransformer().transform_code(code)


def test_assertion_fallbacks_basic():
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
"""
    out = make(code)
    assert "import pytest" in out
    assert "is None" in out
    assert "is not None" in out
    assert " not in " in out
    assert " is " in out
    assert " is not " in out
    assert "sorted([1,2]) == sorted([2,1])" in out


def test_fixtures_created_for_setup_and_teardown():
    code = """
import unittest
class T(unittest.TestCase):
    def setUp(self):
        self.v = 1
    def tearDown(self):
        self.v = None
    def test_a(self):
        self.assertTrue(True)
"""
    out = make(code)
    assert "@pytest.fixture" in out
    assert "def setup_method(self):" in out
    # Single autouse fixture with yield is used; no separate teardown_method required
    assert "def teardown_method(self):" not in out
    assert "yield" in out


def test_class_parentheses_removed_when_no_bases():
    code = """
import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)
"""
    out = make(code)
    assert "class T:" in out
    assert "unittest.TestCase" not in out


def test_nested_and_inheritance_classes():
    code = """
import unittest
class BaseTest(unittest.TestCase):
    def test_base(self):
        self.assertEqual(1,1)
class DerivedTest(BaseTest):
    def test_derived(self):
        self.assertEqual(2,2)
class Outer:
    class TestInner(unittest.TestCase):
        def test_nested(self):
            self.assertTrue(True)
"""
    out = make(code)
    # class headers should not keep empty parentheses
    assert "class BaseTest:" in out
    assert "class DerivedTest(BaseTest):" in out
    assert "class TestInner:" in out


def test_does_not_duplicate_pytest_import():
    code = """
import pytest
import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertEqual(1,1)
"""
    out = make(code)
    assert out.count("import pytest") == 1


def test_all_unittest_assert_variants_exercised():
    code = """
import unittest
class T(unittest.TestCase):
    def test_variants(self):
        # basic equality and truthiness
        self.assertEqual(1+1, 2)
        self.assertTrue(True)
        self.assertFalse(False)
        # identity and None checks
        self.assertIs(1, 1)
        self.assertIsNot(1, 2)
        self.assertIsNone(None)
        self.assertIsNotNone(0)
        # membership
        self.assertIn(1, [1,2,3])
        self.assertNotIn(4, [1,2,3])
        # type checks
        self.assertIsInstance("x", str)
        self.assertNotIsInstance(1, str)
        # collections equality
        self.assertDictEqual({"a":1}, {"a":1})
        self.assertListEqual([1,2], [1,2])
        self.assertSetEqual({1,2}, {2,1})
        self.assertTupleEqual((1,2), (1,2))
        self.assertCountEqual([1,2,2], [2,1,2])
        # regex-related (not yet transformed)
        self.assertRegex("abc", "a.")
        self.assertNotRegex("abc", "z+")
        # raises / raises regex
        with self.assertRaises(ValueError):
            raise ValueError("x")
        with self.assertRaisesRegex(ValueError, "x"):
            raise ValueError("xyz")
"""
    out = make(code)
    assert isinstance(out, str)
    assert "import pytest" in out
    # transformed assertions present
    assert "assert 1+1 == 2" in out or "assert 1 + 1 == 2" in out
    assert "assert True" in out
    assert "assert not False" in out
    assert " is " in out
    assert " is not " in out
    assert " is None" in out
    assert " is not None" in out
    assert " in [1, 2, 3]" in out or " in [1,2,3]" in out
    assert " not in " in out
    assert "isinstance(" in out
    assert "not isinstance(" in out
    assert "==" in out  # covers Dict/List/Set/Tuple equality
    assert "sorted([1,2,2]) == sorted([2,1,2])" in out
    # regex-related: allow either preserved names or transformed re.search forms
    assert "assertRegex" in out or "re.search" in out
    assert "assertNotRegex" in out or "re.search" in out or "not re.search" in out
