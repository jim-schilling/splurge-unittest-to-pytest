import libcst as cst
from splurge_unittest_to_pytest.stages.raises_stage import ExceptionAttrRewriter, RaisesRewriter


def test_exception_attr_rewriter_basic():
    src = """
with pytest.raises(ValueError) as cm:
    pass
print(cm.exception)
"""
    mod = cst.parse_module(src)
    # collect names
    er = ExceptionAttrRewriter("cm")
    out = mod.visit(er)
    assert "cm.value" in out.code


def test_raises_rewriter_callable_form():
    # self.assertRaises(ValueError, func, arg)
    call = cst.Expr(
        cst.Call(
            func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertRaises")),
            args=[cst.Arg(cst.Name("ValueError")), cst.Arg(cst.Name("func")), cst.Arg(cst.Name("arg"))],
        )
    )
    mod = cst.Module(body=[cst.SimpleStatementLine(body=[call])])
    rw = RaisesRewriter()
    out = mod.visit(rw)
    # should contain pytest.raises or a With node
    assert "pytest.raises" in out.code
