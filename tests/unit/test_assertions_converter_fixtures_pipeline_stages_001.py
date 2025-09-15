import libcst as cst

from splurge_unittest_to_pytest.converter.assertions import (
    _assert_is_instance,
    _assert_not_is_instance,
    _assert_in,
    _assert_not_in,
    _assert_greater,
)
from splurge_unittest_to_pytest.converter.fixtures import create_fixture_with_cleanup
from splurge_unittest_to_pytest.stages.pipeline import run_pipeline

DOMAINS = ["assertions", "converter", "fixtures", "pipeline", "stages"]


def _arg(expr: str) -> cst.Arg:
    return cst.Arg(value=cst.parse_expression(expr))


def test_assert_is_instance_helpers():
    a = _arg("obj")
    b = _arg("MyClass")
    n = _assert_is_instance([a, b])
    assert isinstance(n, cst.Assert)
    # the test should be a Call to isinstance
    assert isinstance(n.test, cst.Call)
    assert isinstance(n.test.func, cst.Name) and n.test.func.value == "isinstance"

    # not is instance
    n2 = _assert_not_is_instance([a, b])
    assert isinstance(n2, cst.Assert)
    assert isinstance(n2.test, cst.UnaryOperation)


def test_assert_in_not_in_and_comparison():
    a = _arg("x")
    b = _arg("seq")
    nin = _assert_in([a, b])
    assert isinstance(nin, cst.Assert)
    assert isinstance(nin.test, cst.Comparison)

    nnot = _assert_not_in([a, b])
    assert isinstance(nnot, cst.Assert)
    assert isinstance(nnot.test, cst.Comparison)

    g = _arg("5")
    h = _arg("3")
    ng = _assert_greater([g, h])
    assert isinstance(ng, cst.Assert)
    assert isinstance(ng.test, cst.Comparison)


def test_create_fixture_with_cleanup_yield_and_cleanup():
    # simple cleanup statement: del _x_value
    from libcst import SimpleStatementLine, Expr

    val = cst.parse_expression("'value'")
    # use a valid expression statement for cleanup (print call)
    cleanup = [SimpleStatementLine(body=[Expr(value=cst.parse_expression("print('ok')"))])]
    f = create_fixture_with_cleanup("x", val, cleanup)
    assert isinstance(f, cst.FunctionDef)
    # Ensure the first statement is an assignment to the local value name
    first = f.body.body[0]
    assert isinstance(first, cst.SimpleStatementLine)
    assert isinstance(first.body[0], cst.Assign)
    # The second statement should be a yield of the local value
    second = f.body.body[1]
    assert isinstance(second, cst.SimpleStatementLine)
    assert isinstance(second.body[0], cst.Expr)
    assert isinstance(second.body[0].value, cst.Yield)
    # Ensure cleanup statements were appended after the yield
    assert any(isinstance(s, cst.SimpleStatementLine) for s in f.body.body[2:])


def test_run_pipeline_end_to_end_small_sample():
    src = """
import unittest

class T(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)

"""
    module = cst.parse_module(src)
    out = run_pipeline(module)
    # result should be a Module
    assert isinstance(out, cst.Module)
    # final code should not contain 'unittest.TestCase'
    assert "unittest.TestCase" not in out.code
