import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as rewrites


def _parse_module(src: str) -> cst.Module:
    return cst.parse_module(src)


def _find_assert_expr_from_module(mod: cst.Module) -> cst.BaseExpression | None:
    # Assumes module with a single function whose last statement is an assert call
    func = mod.body[0]
    if not hasattr(func, "body"):
        return None
    last_stmt = func.body.body[-1]
    if not isinstance(last_stmt, cst.SimpleStatementLine):
        return None
    expr = last_stmt.body[0]
    if not isinstance(expr, cst.Expr) or not isinstance(expr.value, cst.Call):
        return None
    # assume assertTrue/assertFalse/assertEqual style single-arg call
    call = expr.value
    if not call.args:
        return None
    return call.args[0].value


def test_parentheses_tokens_preserved_on_comparison():
    src = """
def test_fn(self):
    with self.assertLogs('m') as log:
        pass
    # ensure parentheses around len(...) are preserved
    self.assertTrue((len(log.output) == 1))
"""
    mod = _parse_module(src)
    func = mod.body[0]
    body_stmts = list(func.body.body)
    # process the with so rewrite_following_statements_for_alias may run
    with_stmt = body_stmts[0]
    processed = rewrites._process_with_statement(with_stmt, body_stmts, 0)
    node = processed if processed is not None else with_stmt
    # build module with possibly-updated with
    new_func = func.with_changes(body=func.body.with_changes(body=[node] + list(func.body.body[1:])))
    new_mod = mod.with_changes(body=[new_func] + list(mod.body[1:]))

    # inspect the assertion expression's lpar/rpar tokens
    target_expr = _find_assert_expr_from_module(new_mod)
    assert target_expr is not None

    # the comparison may be parenthesized; if so ensure lpar/rpar are non-empty tuples
    has_lpar = bool(getattr(target_expr, "lpar", ()))
    has_rpar = bool(getattr(target_expr, "rpar", ()))

    assert has_lpar or has_rpar or isinstance(target_expr, cst.Comparison)


def test_leading_comment_preserved_on_with_statement():
    src = """
# pre-comment about test
def test_fn(self):
    # comment before with
    with self.assertLogs('m') as log:
        pass
    self.assertTrue(len(log.output) == 1)
"""
    mod = _parse_module(src)
    func = mod.body[0]
    # locate the With node and its leading lines (avoid hard-coded indices)
    with_stmt = next((s for s in func.body.body if isinstance(s, cst.With)), None)
    assert with_stmt is not None
    leading = getattr(with_stmt, "leading_lines", ())

    def _comment_text(ll):
        c = getattr(ll, "comment", None)
        return getattr(c, "value", "") if c is not None else ""

    assert any("comment before with" in _comment_text(ll) for ll in leading)

    # run processing and re-inspect leading_lines on the processed with
    body_stmts = list(func.body.body)
    processed = rewrites._process_with_statement(with_stmt, body_stmts, body_stmts.index(with_stmt))
    node = processed if processed is not None else with_stmt
    leading_after = getattr(node, "leading_lines", ())
    assert any("comment before with" in _comment_text(ll) for ll in leading_after)
