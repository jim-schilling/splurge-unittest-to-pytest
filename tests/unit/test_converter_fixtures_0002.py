import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_body import build_fixture_body


def test_build_fixture_body_with_simple_literal_preserves_cleanup():
    value_expr = cst.Integer(value="1")
    cleanup = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Call(func=cst.Name("cleanup_fn"), args=[]))])]
    body = build_fixture_body("attr", value_expr, cleanup)
    assert isinstance(body, cst.IndentedBlock)
    stmts = body.body
    assert isinstance(stmts[0], cst.SimpleStatementLine)
    expr = stmts[0].body[0]
    assert isinstance(expr, cst.Expr)
    assert isinstance(expr.value, cst.Yield)
    assert isinstance(expr.value.value, cst.Integer)
    assert expr.value.value.value == "1"
    assert len(stmts) == 1 + len(cleanup)
    assert isinstance(stmts[1], cst.SimpleStatementLine)


def test_build_fixture_body_with_complex_value_assigns_and_rewrites_cleanup():
    attr_name = "myattr"
    value_expr = cst.Call(func=cst.Name("compute"), args=[])
    cleanup = [
        cst.SimpleStatementLine(body=[cst.Expr(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name(attr_name)))]),
        cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(attr_name))]),
    ]
    body = build_fixture_body(attr_name, value_expr, cleanup)
    stmts = body.body
    assert isinstance(stmts[0], cst.SimpleStatementLine)
    assign = stmts[0].body[0]
    assert isinstance(assign, cst.Assign)
    target = assign.targets[0].target
    assert isinstance(target, cst.Name)
    expected_name = f"_{attr_name}_value"
    assert target.value == expected_name
    yield_stmt = stmts[1].body[0]
    assert isinstance(yield_stmt, cst.Expr)
    assert isinstance(yield_stmt.value, cst.Yield)
    assert isinstance(yield_stmt.value.value, cst.Name)
    assert yield_stmt.value.value.value == expected_name

    class NameCollector(cst.CSTVisitor):
        def __init__(self):
            self.names = []

        def visit_Name(self, node: cst.Name) -> None:
            self.names.append(node.value)

    collector = NameCollector()
    for s in stmts[2:]:
        s.visit(collector)
    assert expected_name in collector.names
    assert attr_name not in collector.names
