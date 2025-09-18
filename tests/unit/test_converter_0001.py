import libcst as cst
from splurge_unittest_to_pytest.converter.class_checks import is_unittest_testcase_base
from typing import cast
from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator
from splurge_unittest_to_pytest.converter.placement import insert_fixtures_into_module
from splurge_unittest_to_pytest.converter.setup_parser import parse_setup_assignments


def _make_attr(base_src: str) -> cst.Arg:
    module = cst.parse_module(base_src)
    expr = module.body[0].body[0].value
    return cst.Arg(value=expr)


def test_unittest_testcase_attribute():
    arg = _make_attr("unittest.TestCase")
    assert is_unittest_testcase_base(arg)


def test_bare_testcase_name():
    arg = _make_attr("TestCase")
    assert is_unittest_testcase_base(arg)


def test_non_testcase_returns_false():
    arg = _make_attr("object")
    assert not is_unittest_testcase_base(arg)


def render(node: cst.CSTNode) -> str:
    return cst.Module(body=[cst.SimpleStatementLine([cst.Expr(cast(cst.BaseExpression, node))])]).code.strip()


def test_build_basic_fixture_decorator():
    dec = build_pytest_fixture_decorator()
    code = render(dec)
    assert "@pytest.fixture" in code


def test_build_fixture_decorator_accepts_kwargs():
    dec = build_pytest_fixture_decorator(scope="module", autouse=True)
    code = cst.Module(
        body=[cst.SimpleStatementLine(body=[cst.Expr(value=cast(cst.BaseExpression, dec.decorator))])]
    ).code
    # libcst may render spacing around '=' and order kwargs; check tokens instead
    assert "pytest.fixture" in code and "autouse" in code and "module" in code


def test_build_pytest_fixture_decorator_renders_pytest_fixture():
    dec = build_pytest_fixture_decorator()
    code = cst.Module(
        body=[cst.SimpleStatementLine(body=[cst.Expr(value=cast(cst.BaseExpression, dec.decorator))])]
    ).code
    assert "pytest.fixture" in code


def test_insert_fixtures_after_imports():
    module = cst.Module(
        body=[
            cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])]),
            cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Name("setup"), args=[]))]),
        ]
    )
    fixture_func = cst.FunctionDef(
        name=cst.Name("my_fixture"),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )
    new_mod = insert_fixtures_into_module(module, {"my_fixture": fixture_func})
    assert any((isinstance(n, cst.FunctionDef) for n in new_mod.body))


def test_parse_setup_assignments_extracts_self_attrs():
    src = "\ndef setUp(self):\n    self.foo = 1\n    self.bar = 'x'\n    other = 2\n"
    module = cst.parse_module(src)
    func = None
    for node in module.body:
        if isinstance(node, cst.FunctionDef) and node.name.value == "setUp":
            func = node
            break
    assert func is not None
    assignments = parse_setup_assignments(func)
    assert "foo" in assignments
    assert "bar" in assignments
    assert "other" not in assignments
