import libcst as cst

from splurge_unittest_to_pytest.converter.assertions import (
    _assert_greater,
    _assert_greater_equal,
    _assert_in,
    _assert_is_instance,
    _assert_less,
    _assert_less_equal,
    _assert_not_in,
    _assert_not_is_instance,
)
from splurge_unittest_to_pytest.converter.fixtures import create_fixture_for_attribute, create_fixture_with_cleanup
from splurge_unittest_to_pytest.stages.pipeline import run_pipeline


def _arg(expr: str) -> cst.Arg:
    return cst.Arg(value=cst.parse_expression(expr))


def test_assert_is_instance_helpers():
    a = _arg("obj")
    b = _arg("MyClass")
    n = _assert_is_instance([a, b])
    assert isinstance(n, cst.Assert)
    assert isinstance(n.test, cst.Call)
    assert isinstance(n.test.func, cst.Name) and n.test.func.value == "isinstance"
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
    from libcst import Expr, SimpleStatementLine

    val = cst.parse_expression("'value'")
    cleanup = [SimpleStatementLine(body=[Expr(value=cst.parse_expression("print('ok')"))])]
    f = create_fixture_with_cleanup("x", val, cleanup)
    assert isinstance(f, cst.FunctionDef)
    first = f.body.body[0]
    assert isinstance(first, cst.SimpleStatementLine)
    assert isinstance(first.body[0], cst.Assign)
    second = f.body.body[1]
    assert isinstance(second, cst.SimpleStatementLine)
    assert isinstance(second.body[0], cst.Expr)
    assert isinstance(second.body[0].value, cst.Yield)
    assert any((isinstance(s, cst.SimpleStatementLine) for s in f.body.body[2:]))


def test_run_pipeline_end_to_end_small_sample():
    src = (
        "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_one(self):\n        self.assertEqual(1, 1)\n\n"
    )
    module = cst.parse_module(src)
    out = run_pipeline(module)
    assert isinstance(out, cst.Module)
    assert "unittest.TestCase" not in out.code


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
    obj = _a("o")
    klass = _a("K")
    ni = _assert_not_is_instance([obj, klass])
    assert isinstance(ni, cst.Assert)
    assert isinstance(ni.test, cst.UnaryOperation)


def test_create_fixture_for_attribute_delegates_and_simple_case():
    val = cst.parse_expression("100")
    f = create_fixture_for_attribute("v", val, {})
    assert isinstance(f, cst.FunctionDef)


def test_end_to_end_setup_teardown_with_cleanup():
    src = "\nimport unittest\n\nclass MyTest(unittest.TestCase):\n    def setUp(self):\n        self.x = 1\n\n    def tearDown(self):\n        del self.x\n\n    def test_it(self):\n        self.assertEqual(self.x, 1)\n\n"
    module = cst.parse_module(src)
    out = run_pipeline(module)
    assert isinstance(out, cst.Module)
    code = out.code
    assert "unittest.TestCase" not in code
    assert "def " in code
