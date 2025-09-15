import libcst as cst

from splurge_unittest_to_pytest.converter import raises

DOMAINS = ["core"]


def test_make_pytest_raises_call_defaults_and_explicit():
    # no args -> defaults to Exception
    call = raises.make_pytest_raises_call([])
    assert "Exception" in cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=call)])]).code

    # explicit exception arg
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
    # render the with item inside a with to see code
    with_node = cst.With(items=[wi], body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]))
    code = cst.Module(body=[with_node]).code
    assert "pytest.raises" in code
