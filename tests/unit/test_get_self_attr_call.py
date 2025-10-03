import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def test_get_self_attr_call_finds_method_call():
    stmt = cst.SimpleStatementLine(
        body=[
            cst.Expr(
                value=cst.Call(func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="foo")), args=[])
            )
        ]
    )
    out = aw.get_self_attr_call(stmt)
    assert out is not None
    name, call = out
    assert name == "foo"
    assert isinstance(call, cst.Call)


def test_get_self_attr_call_none_for_other_shapes():
    stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="x"))])
    assert aw.get_self_attr_call(stmt) is None
