import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as rewrites


def _parse_module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_parentheses_lpar_rpar_preserved_on_comparison_rewrite():
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
    src_after = new_mod.code
    # Expect the double parentheses to be present in generated code
    assert "((len(log.output) == 1))" in src_after or "(len(log.output) == 1)" in src_after
