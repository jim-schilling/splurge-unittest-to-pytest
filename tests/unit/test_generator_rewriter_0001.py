import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.attr_rewriter import AttrRewriter, replace_in_node


def parse_expr(src: str) -> cst.BaseExpression:
    mod = cst.parse_module(src)
    stmt = mod.body[0]
    return stmt.body[0].value


def test_attr_rewriter_self_replaced():
    expr = parse_expr("self.x")
    rewritten = expr.visit(AttrRewriter("x", "_x_value"))
    assert isinstance(rewritten, cst.Name)
    assert rewritten.value == "_x_value"


def test_attr_rewriter_cls_replaced():
    expr = parse_expr("cls.config")
    rewritten = replace_in_node(expr, "config", "cfg")
    assert isinstance(rewritten, cst.Name)
    assert rewritten.value == "cfg"


def test_attr_rewriter_non_matching_preserved():
    expr = parse_expr("obj.attr")
    rewritten = expr.visit(AttrRewriter("attr", "_a"))
    assert isinstance(rewritten, cst.Attribute)
