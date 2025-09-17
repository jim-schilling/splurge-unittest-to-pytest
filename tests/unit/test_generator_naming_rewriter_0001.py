import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts import filename_inferer, attr_rewriter, replace_self_param


class Dummy:
    pass


def test_infer_filename_simple_string():
    d = Dummy()
    call = cst.Call(func=cst.Name("helper"), args=[cst.Arg(value=cst.SimpleString('"file.txt"'))])
    d.local_assignments = {"cfg": (call, None)}
    assert filename_inferer.infer_filename_for_local("cfg", d) == "file.txt"


def test_infer_filename_non_call_or_missing():
    d = Dummy()
    d.local_assignments = {"cfg": (cst.Name("x"), None)}
    assert filename_inferer.infer_filename_for_local("cfg", d) is None
    assert filename_inferer.infer_filename_for_local("missing", d) is None


def test_attr_rewriter_replaces_self_attr():
    expr = cst.parse_expression("self.x")
    out = attr_rewriter.replace_in_node(expr, "x", "_x")
    assert isinstance(out, cst.Name)
    assert out.value == "_x"


def test_replace_self_with_param():
    expr = cst.parse_expression("self.val + 1")
    out = expr.visit(replace_self_param.ReplaceSelfWithParam({"val"}))
    s = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(out)])]).code
    assert "self.val" not in s
    assert "val" in s
