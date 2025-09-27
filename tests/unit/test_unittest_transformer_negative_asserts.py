import pytest

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCSTTransformer as UnittestToPytestTransformer,
)


def make(code: str) -> str:
    return UnittestToPytestTransformer().transform_code(code)


def test_malformed_self_assert_variants_are_ignored():
    """Single input containing malformed variants of every supported self.assert*.

    The transformer should not raise and should leave (or at least not incorrectly transform)
    obviously malformed self.assert calls. This is a negative/regression test to ensure
    the string-based replacements are safe on bad inputs.
    """
    code = """
import unittest

class T(unittest.TestCase):
    def test_malformed(self):
        # insufficient args / malformed parentheses
        self.assertEqual(1)
        self.assertEquals()
        self.assertNotEqual(
        self.assertNotEquals(,)

        # one-arg assertions with missing expressions
        self.assertTrue()
        self.assertIsTrue(
        self.assertFalse()
        self.assertIsFalse(

        # identity and None checks malformed
        self.assertIs(1)
        self.assertIsNot()
        self.assertIsNone()
        self.assertIsNotNone(

        # membership malformed
        self.assertIn(, [1,2])
        self.assertNotIn(1,)

        # isinstance malformed
        self.assertIsInstance()
        self.assertNotIsInstance(1)

        # collections malformed
        self.assertListEqual([1,2])
        self.assertDictEqual({})
        self.assertSetEqual({1,})
        self.assertTupleEqual((1,))
        self.assertCountEqual([1,2])

        # raises / regex malformed (used in with contexts normally)
        with self.assertRaises():
            pass
        with self.assertRaisesRegex(ValueError):
            pass

        # regex assertions malformed
        self.assertRegex()
        self.assertNotRegex(,)

        # intentionally broken syntax lines that are still strings in file
        self.assertEqual 1, 2)
        self.assertTrue(True

"""

    out = make(code)

    # Transformation should return a string and should not crash
    assert isinstance(out, str)

    # Check that many of the malformed markers are still present (i.e., not incorrectly transformed)
    assert "self.assertEqual(1)" in out or "self.assertEqual 1, 2)" in out
    assert "self.assertTrue()" in out
    assert "self.assertIsNot()" in out
    assert "self.assertIn(, [1,2])" in out or "self.assertNotIn(1,)" in out
    assert "with self.assertRaises()" in out
    assert "self.assertRegex()" in out
