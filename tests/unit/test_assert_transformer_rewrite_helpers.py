import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    rewrite_asserts_using_alias_in_with_body,
    rewrite_following_statements_for_alias,
)


def _parse_stmt(src: str) -> cst.BaseStatement:
    mod = cst.parse_module(src)
    # Return first top-level statement
    return mod.body[0]


def test_rewrite_len_in_with_body_subscript_index():
    src = """
with caplog as log:
    assert len(log.output[0]) == 2
"""
    with_stmt = _parse_stmt(src)
    assert isinstance(with_stmt, cst.SimpleStatementLine) or isinstance(with_stmt, cst.With)
    # If parse gives SimpleStatementLine for 'with' (libcst behavior), reparse as module
    mod = cst.parse_module(src)
    w = mod.body[0]
    assert isinstance(w, cst.With)

    new_with = rewrite_asserts_using_alias_in_with_body(w, "log")
    # Ensure caplog.records appears in the transformed tree
    assert "caplog" in repr(new_with)
    assert "records" in repr(new_with)


def test_rewrite_membership_in_with_body_getmessage():
    src = """
with caplog as log:
    assert 'error' in log.output[0]
"""
    mod = cst.parse_module(src)
    w = mod.body[0]
    new_with = rewrite_asserts_using_alias_in_with_body(w, "log")
    r = repr(new_with)
    assert "caplog" in r
    # membership should include getMessage() call
    assert "getMessage" in r


def test_rewrite_assert_equal_self_inside_with_body():
    src = """
with caplog as log:
    self.assertEqual(len(log.output), 3)
"""
    mod = cst.parse_module(src)
    w = mod.body[0]
    new_with = rewrite_asserts_using_alias_in_with_body(w, "log")
    r = repr(new_with)
    assert "caplog" in r


def test_rewrite_following_statements_len_and_membership():
    src = """
# preceding block
with caplog as log:
    pass
assert len(log.output) == 1
assert 'oops' in log.output[0]
"""
    mod = cst.parse_module(src)
    stmts = list(mod.body)
    # find index of the with
    idx = 0
    for i, s in enumerate(stmts):
        if isinstance(s, cst.With):
            idx = i
            break
    # mutate following statements in place
    rewrite_following_statements_for_alias(stmts, idx + 1, "log")
    joined = "\n".join(repr(s) for s in stmts)
    assert "caplog" in joined
    assert "getMessage" in joined
