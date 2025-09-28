import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    rewrite_asserts_using_alias_in_with_body,
    rewrite_following_statements_for_alias,
    transform_with_items,
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


def test_preserve_asname_for_raises_with_item():
    # Build a With node representing: with self.assertRaises(ValueError) as cm: pass
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertRaises")),
            args=[cst.Arg(value=cst.Name(value="ValueError"))],
        ),
        asname=cst.AsName(name=cst.Name(value="cm")),
    )
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))])])
    w = cst.With(items=[with_item], body=body)

    new_with, alias_name, changed = transform_with_items(w)
    assert changed
    # transformed item should call pytest.raises and preserve the asname
    assert "pytest" in repr(new_with.items[0].item)
    assert new_with.items[0].asname is not None
    assert isinstance(new_with.items[0].asname.name, cst.Name)
    assert new_with.items[0].asname.name.value == "cm"


def test_caplog_default_level_added_when_missing():
    # Build With node representing: with self.assertLogs("foo"):
    with_item = cst.WithItem(
        item=cst.Call(
            func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value="assertLogs")),
            args=[cst.Arg(value=cst.SimpleString(value='"foo"'))],
        ),
    )
    body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(value="pass"))])])
    w = cst.With(items=[with_item], body=body)

    new_with, alias_name, changed = transform_with_items(w)
    assert changed
    r = repr(new_with)
    assert "caplog" in r
    assert '"INFO"' in r or "INFO" in r


def test_lookahead_rewrites_equality_rhs_getmessage():
    src = """
with caplog as log:
    pass
assert log.output[0] == 'bad'
"""
    mod = cst.parse_module(src)
    stmts = list(mod.body)
    # find index of the with
    idx = 0
    for i, s in enumerate(stmts):
        if isinstance(s, cst.With):
            idx = i
            break
    rewrite_following_statements_for_alias(stmts, idx + 1, "log")
    joined = "\n".join(repr(s) for s in stmts)
    # RHS equality should be rewritten to caplog.records[0].getMessage() or similar
    assert "caplog" in joined
    assert "getMessage" in joined
