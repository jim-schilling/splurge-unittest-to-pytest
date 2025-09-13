import libcst as cst
from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer


def _apply(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_decorator_factory_expected_and_skip():
    src = """
import unittest

def deco(x):
    def _d(fn):
        return fn
    return _d

class T(unittest.TestCase):
    @deco(1)
    @unittest.expectedFailure
    def test_a(self):
        assert 1 == 2

    @deco(0)
    @unittest.skip('skip it')
    def test_b(self):
        assert False
"""
    out = _apply(src)
    assert "pytest.mark.xfail" in out
    assert "pytest.mark.skip" in out
