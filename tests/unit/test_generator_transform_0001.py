import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts import transformers


def _parse_expr(src: str) -> cst.BaseExpression:
    module = cst.parse_module(src)
    stmt = module.body[0]
    return stmt.body[0].value


def test_replace_self_with_name_simple():
    expr = _parse_expr("self.x")
    new = expr.visit(transformers.ReplaceSelfWithName())
    assert isinstance(new, cst.Name)
    assert new.value == "x"


def test_replace_self_with_name_chain():
    expr = _parse_expr("self.inner.attr")
    new = expr.visit(transformers.ReplaceSelfWithName())
    assert isinstance(new, cst.Name)
    assert new.value == "attr"


def test_replace_attr_with_local_mapping():
    expr = _parse_expr("obj.prop")
    new = expr.visit(transformers.ReplaceAttrWithLocal({"obj": "local"}))
    assert isinstance(new, cst.Name)
    assert new.value == "local__prop"


def test_replace_self_name_occurrence():
    expr = _parse_expr("self")
    new = expr.visit(transformers.ReplaceSelf("_self_local"))
    assert isinstance(new, cst.Name)
    assert new.value == "_self_local"


def test_replace_name_with_local():
    expr = _parse_expr("x + 1")
    new = expr.visit(transformers.ReplaceNameWithLocal("x", "_x_local"))
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(new)])]).code
    assert "_x_local" in code
