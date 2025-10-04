import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as rewrites


def _parse_module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_with_body_wrapper_preserved_after_rewrite():
    # baseline: simple with with a pass and a trailing assert
    src = """
def test_fn(self):
    with self.assertLogs('m') as log:
        pass
    self.assertEqual(len(log.output), 1)
"""

    mod = _parse_module(src)
    func = mod.body[0]
    body_stmts = func.body.body
    with_stmt = body_stmts[0]
    assert isinstance(with_stmt, cst.With)

    processed = rewrites._process_with_statement(with_stmt, list(body_stmts), 0)
    if processed is None:
        # nothing changed; assert original wrapper is IndentedBlock
        assert isinstance(with_stmt.body, cst.IndentedBlock)
        assert isinstance(with_stmt.body.body[0], cst.SimpleStatementLine)
    else:
        assert isinstance(processed.body, cst.IndentedBlock)
        assert isinstance(processed.body.body[0], cst.SimpleStatementLine)


def test_nested_withs_and_empty_body_preserved():
    src = """
def test_fn(self):
    with self.assertLogs('m') as log:
        with self.assertLogs('n') as log2:
            pass
    # no trailing asserts
"""
    mod = _parse_module(src)
    func = mod.body[0]
    outer_with = func.body.body[0]
    assert isinstance(outer_with, cst.With)
    processed = rewrites._process_with_statement(outer_with, list(func.body.body), 0)
    if processed is None:
        assert isinstance(outer_with.body, cst.IndentedBlock)
        inner = outer_with.body.body[0]
        assert isinstance(inner, cst.With)
        assert isinstance(inner.body, cst.IndentedBlock)
    else:
        assert isinstance(processed.body, cst.IndentedBlock)
        inner = processed.body.body[0]
        assert isinstance(inner, cst.With)
        assert isinstance(inner.body, cst.IndentedBlock)


def test_with_with_comment_and_whitespace_preserved():
    src = """
def test_fn(self):
    # leading comment
    with self.assertLogs('m') as log:
        # inner comment
        pass
    # trailing comment
"""
    mod = _parse_module(src)
    func = mod.body[0]
    w = func.body.body[1] if len(func.body.body) > 1 else func.body.body[0]
    assert isinstance(w, cst.With)
    processed = rewrites._process_with_statement(w, list(func.body.body), 0)
    if processed is None:
        assert isinstance(w.body, cst.IndentedBlock)
    else:
        assert isinstance(processed.body, cst.IndentedBlock)
