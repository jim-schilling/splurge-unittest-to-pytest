import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as rewrites


def _parse_module(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_comments_and_blank_lines_preserved_after_with_rewrite():
    src = '''
def test_fn(self):
    # leading comment A
    with self.assertLogs('m') as log:
        # inner comment B
        pass

    # trailing comment C

    self.assertEqual(len(log.output), 1)
'''

    mod = _parse_module(src)
    func = mod.body[0]
    body_stmts = func.body.body
    with_stmt = body_stmts[0]
    assert isinstance(with_stmt, cst.With)

    processed = rewrites._process_with_statement(with_stmt, list(body_stmts), 0)
    # Whether processed or not we expect the wrapper body to be an IndentedBlock
    node = processed if processed is not None else with_stmt
    assert isinstance(node.body, cst.IndentedBlock)
    # stringify and ensure leading/inner/trailing comments remain in source
    # Build a new module with the processed node replacing the original
    new_func = func.with_changes(body=func.body.with_changes(body=[node] + list(func.body.body[1:])))
    new_mod = mod.with_changes(body=[new_func] + list(mod.body[1:]))
    src_after = new_mod.code
    assert "# leading comment A" in src_after
    assert "# inner comment B" in src_after
    assert "# trailing comment C" in src_after


def test_empty_body_with_comment_preserved():
    src = '''
def test_fn(self):
    with self.assertLogs('m') as log:
        # only a comment here
        pass

    self.assertEqual(len(log.output), 1)
'''
    mod = _parse_module(src)
    func = mod.body[0]
    body_stmts = func.body.body
    with_stmt = body_stmts[0]
    processed = rewrites._process_with_statement(with_stmt, list(body_stmts), 0)
    node = processed if processed is not None else with_stmt
    assert isinstance(node.body, cst.IndentedBlock)
    new_func = func.with_changes(body=func.body.with_changes(body=[node] + list(func.body.body[1:])))
    new_mod = mod.with_changes(body=[new_func] + list(mod.body[1:]))
    src_after = new_mod.code
    assert "# only a comment here" in src_after
