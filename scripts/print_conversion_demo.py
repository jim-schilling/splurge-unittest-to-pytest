"""Standalone demo: print original unittest source and the transformed pytest source.

Run with the project's virtualenv python, e.g.:

D:/repos/splurge-unittest-to-pytest/.venv/Scripts/python -u scripts/print_conversion_demo.py
"""

import sys
import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)

original = textwrap.dedent(
    """
import unittest


class MyTests(unittest.TestCase):
    def test_numbers(self):
        test_cases = [(1, True), (0, False), (2, True)]
        for n, expected in test_cases:
            with self.subTest(n=n):
                assert (n % 2 == 1) == expected
"""
)

transformer = UnittestToPytestCstTransformer(parametrize=True)
converted = transformer.transform_code(original)

sys.stdout.write("--- ORIGINAL ---\n")
sys.stdout.write(original + "\n")
sys.stdout.write("--- CONVERTED ---\n")
sys.stdout.write(converted + "\n")
sys.stdout.flush()
