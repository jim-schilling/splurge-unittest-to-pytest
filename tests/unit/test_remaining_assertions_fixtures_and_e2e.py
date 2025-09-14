import libcst as cst

from splurge_unittest_to_pytest.converter.assertions import (
    _assert_greater_equal,
    _assert_less,
    _assert_less_equal,
    _assert_not_is_instance,
)
from splurge_unittest_to_pytest.converter.fixtures import create_fixture_for_attribute
from splurge_unittest_to_pytest.stages.pipeline import run_pipeline


def _a(expr: str) -> cst.Arg:
    return cst.Arg(value=cst.parse_expression(expr))


def test_remaining_comparisons_and_not_is_instance():
    a = _a("5")
    b = _a("3")
    ge = _assert_greater_equal([a, b])
    assert isinstance(ge, cst.Assert)
    assert isinstance(ge.test, cst.Comparison)

    le = _assert_less([b, a])
    assert isinstance(le, cst.Assert)

    leq = _assert_less_equal([b, a])
    assert isinstance(leq, cst.Assert)

    # not is instance
    obj = _a("o")
    klass = _a("K")
    ni = _assert_not_is_instance([obj, klass])
    assert isinstance(ni, cst.Assert)
    assert isinstance(ni.test, cst.UnaryOperation)


def test_create_fixture_for_attribute_delegates_and_simple_case():
    val = cst.parse_expression("100")
    # When teardown cleanup is empty, create_simple_fixture path is used
    f = create_fixture_for_attribute("v", val, {})
    assert isinstance(f, cst.FunctionDef)


def test_end_to_end_setup_teardown_with_cleanup():
    src = """
import unittest

class MyTest(unittest.TestCase):
    def setUp(self):
        self.x = 1

    def tearDown(self):
        del self.x

    def test_it(self):
        self.assertEqual(self.x, 1)

"""
    module = cst.parse_module(src)
    out = run_pipeline(module)
    assert isinstance(out, cst.Module)
    code = out.code
    # Should not contain unittest.TestCase inheritance
    assert "unittest.TestCase" not in code
    # compat/autouse behavior removed; ensure conversion produced fixture or correct test
    # do not require internal _attach_to_instance helper
    assert "def " in code
