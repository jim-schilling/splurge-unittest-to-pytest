import libcst as cst
from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer


def _apply_transformer(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_mock_star_and_aliases_remain_valid():
    src = """
import unittest
from unittest.mock import *
import unittest.mock as m
from unittest.mock import Mock as M, patch as p

class X(unittest.TestCase):
    def test(self):
        m = M()
        self.assertIsNotNone(m)
"""
    out = _apply_transformer(src)
    # output must be syntactically valid Python
    cst.parse_module(out)
    # ensure we either preserved star import or have module import
    assert (
        ("from unittest.mock import *" in out)
        or ("import unittest.mock as mock" in out)
        or ("import unittest.mock as m" in out)
    )
