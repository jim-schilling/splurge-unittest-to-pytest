import libcst as cst
from splurge_unittest_to_pytest.converter import raises


def test_make_pytest_raises_call_defaults_and_explicit():
    call = raises.make_pytest_raises_call([])
    assert "Exception" in cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=call)])]).code
    arg = cst.Arg(value=cst.Name("ValueError"))
    call2 = raises.make_pytest_raises_call([arg])
    assert "ValueError" in cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=call2)])]).code


def test_make_pytest_raises_regex_call_match_kw():
    exc = cst.Arg(value=cst.Name("KeyError"))
    pat = cst.Arg(value=cst.SimpleString("'oops'"))
    call = raises.make_pytest_raises_regex_call([exc, pat])
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=call)])]).code
    assert "match=" in code or "'oops'" in code


def test_create_pytest_raises_withitem_variants():
    exc = cst.Arg(value=cst.Name("RuntimeError"))
    wi = raises.create_pytest_raises_withitem("assertRaises", [exc])
    with_node = cst.With(items=[wi], body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]))
    code = cst.Module(body=[with_node]).code
    assert "pytest.raises" in code


def make_arg(value_expr: cst.BaseExpression) -> cst.Arg:
    return cst.Arg(value=value_expr)


def test_make_pytest_raises_call_defaults_and_arg():
    node = raises.make_pytest_raises_call([])
    assert isinstance(node, cst.Call)
    assert isinstance(node.func, cst.Attribute) and node.func.attr.value == "raises"
    a = make_arg(cst.Name("ValueError"))
    node2 = raises.make_pytest_raises_call([a])
    assert isinstance(node2, cst.Call)
    assert node2.args[0] is a


def test_make_pytest_raises_regex_call_and_withitem():
    exc = make_arg(cst.Name("KeyError"))
    regex = make_arg(cst.SimpleString('"pattern"'))
    node = raises.make_pytest_raises_regex_call([exc, regex])
    assert isinstance(node, cst.Call)
    assert any((arg.keyword and getattr(arg.keyword, "value", None) == "match" for arg in node.args))
    with_item = raises.create_pytest_raises_withitem("assertRaises", [exc])
    assert isinstance(with_item, cst.WithItem)
    with_item2 = raises.create_pytest_raises_withitem("assertRaisesRegex", [exc, regex])
    assert isinstance(with_item2, cst.WithItem)
