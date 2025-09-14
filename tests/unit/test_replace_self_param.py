import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.replace_self_param import ReplaceSelfWithParam


def parse_expr(src: str) -> cst.BaseExpression:
    return cst.parse_expression(src)


def test_replace_self_with_param_replaces():
    expr = parse_expr("self.foo")
    rewritten = expr.visit(ReplaceSelfWithParam({"foo"}))
    assert isinstance(rewritten, cst.Name)
    assert rewritten.value == "foo"


def test_replace_non_self_preserved():
    expr = parse_expr("obj.bar")
    rewritten = expr.visit(ReplaceSelfWithParam({"bar"}))
    assert isinstance(rewritten, cst.Attribute)
