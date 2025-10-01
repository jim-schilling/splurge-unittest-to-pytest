import libcst as cst


def test_expression_is_constant_and_name_collection():
    from splurge_unittest_to_pytest.transformers import parametrize_helper as ph

    # simple literals
    assert ph._expression_is_constant(cst.Integer(value="3"))
    assert ph._expression_is_constant(cst.SimpleString(value='"x"'))

    # unary op around literal (use parser to avoid library enum differences)
    expr = cst.parse_expression("-1")
    assert ph._expression_is_constant(expr)

    # collection of constants
    lst = cst.List(elements=[cst.Element(value=cst.Integer(value="1")), cst.Element(value=cst.Integer(value="2"))])
    assert ph._expression_is_constant(lst)

    # complex: binary op of constants
    binop = cst.BinaryOperation(left=cst.Integer(value="1"), operator=cst.Add(), right=cst.Integer(value="2"))
    assert ph._expression_is_constant(binop)

    # name collection
    name_expr = cst.parse_expression("a + b")
    names = ph._collect_expression_names(name_expr)
    assert "a" in names and "b" in names
