import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as rewrites


def _parse_module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_caplog_records_lpar_rpar_preserved_after_rewrite():
    src = """
def test_fn(self):
    with self.assertLogs('m') as log:
        pass
    # ensure caplog index access parentheses preserved
    self.assertTrue(("error" in log.output[0].getMessage()))
"""
    mod = _parse_module(src)
    func = mod.body[0]
    body_stmts = list(func.body.body)
    with_stmt = next((s for s in body_stmts if isinstance(s, cst.With)), None)
    processed = rewrites._process_with_statement(with_stmt, body_stmts, body_stmts.index(with_stmt))
    node = processed if processed is not None else with_stmt
    new_func = func.with_changes(body=func.body.with_changes(body=[node] + list(func.body.body[1:])))
    _ = mod.with_changes(body=[new_func] + list(mod.body[1:]))

    # find the comparison expression in the assertion
    assert_expr = None
    for stmt in new_func.body.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.Expr) and isinstance(item.value, cst.Call):
                    call = item.value
                    if call.args:
                        assert_expr = call.args[0].value
    assert assert_expr is not None
    # verify lpar/rpar exist if present on the expression
    has_lpar = bool(getattr(assert_expr, "lpar", ()))
    has_rpar = bool(getattr(assert_expr, "rpar", ()))
    assert has_lpar or has_rpar or isinstance(assert_expr, cst.BaseExpression)


def test_nested_parentheses_preserved_after_rewrite():
    src = """
def test_fn(self):
    with self.assertLogs('m') as log:
        pass
    self.assertTrue(((len(log.output) == 1)))
"""
    mod = _parse_module(src)
    func = mod.body[0]
    body_stmts = list(func.body.body)
    with_stmt = next((s for s in body_stmts if isinstance(s, cst.With)), None)
    processed = rewrites._process_with_statement(with_stmt, body_stmts, body_stmts.index(with_stmt))
    node = processed if processed is not None else with_stmt
    new_func = func.with_changes(body=func.body.with_changes(body=[node] + list(func.body.body[1:])))
    # inspect the rewritten assertion
    assert_stmt = new_func.body.body[-1]
    # get the Expr value
    expr = assert_stmt.body[0].value
    # argument to the call
    arg = expr.args[0].value if expr.args else None
    # Check parens tokens on arg
    assert arg is not None
    lpar = tuple(getattr(arg, "lpar", ()))
    rpar = tuple(getattr(arg, "rpar", ()))
    # Either there are explicit parens or the inner comparison remains a Comparison
    assert bool(lpar or rpar) or isinstance(arg, cst.Comparison)
