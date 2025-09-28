import pytest

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def make(code: str) -> str:
    return UnittestToPytestCstTransformer().transform_code(code)


def test_all_assert_variants_transformed_by_cst_where_possible():
    code = """
import unittest

class T(unittest.TestCase):
    def test_all(self):
        self.assertEqual(1, 1)
        self.assertTrue(True)
        self.assertFalse(False)
        self.assertIs(1, 1)
        self.assertIsNot(1, 2)
        self.assertIsNone(None)
        self.assertIsNotNone(0)
        self.assertIn(1, [1,2,3])
        self.assertNotIn(4, [1,2,3])
        self.assertIsInstance('x', str)
        self.assertNotIsInstance(1, str)
        self.assertDictEqual({'a':1}, {'a':1})
        self.assertListEqual([1,2], [1,2])
        self.assertSetEqual({1,2}, {2,1})
        self.assertTupleEqual((1,2), (1,2))
        self.assertCountEqual([1,2,2], [2,1,2])
        with self.assertRaises(ValueError):
            raise ValueError('x')
        with self.assertRaisesRegex(ValueError, 'x'):
            raise ValueError('xyz')
"""

    out = make(code)

    assert isinstance(out, str)
    # Basic checks for transformed assertions
    # libcst may produce parenthesized assert(...) or plain assert expressions; accept both
    assert ("assert 1 == 1" in out) or ("assert(1 == 1)" in out)
    assert ("assert True" in out) or ("assert(True)" in out)
    assert ("assert not False" in out) or ("assert(not False)" in out)
    assert ("assert 1 is 1" in out) or ("assert(1 is 1)" in out)
    assert ("assert 1 is not 2" in out) or ("assert(1 is not 2)" in out)
    assert "is None" in out
    assert "is not None" in out
    assert " in [1, 2, 3]" in out or " in [1,2,3]" in out
    assert "isinstance(" in out
    assert "not isinstance(" in out
    assert ("sorted([1, 2, 2]) == sorted([2, 1, 2])" in out) or ("sorted([1,2,2]) == sorted([2,1,2])" in out)
    assert "pytest.raises" in out
