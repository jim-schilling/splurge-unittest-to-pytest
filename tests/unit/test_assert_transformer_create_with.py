import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    build_with_item_from_assert_call,
    create_with_wrapping_next_stmt,
)


def test_create_with_wrapping_next_stmt_with_next_statement():
    call = cst.parse_expression("self.assertLogs('x')")
    assert isinstance(call, cst.Call)
    wi = build_with_item_from_assert_call(call)
    assert wi is not None

    next_stmt = cst.parse_statement("print('hi')")
    with_node, consumed = create_with_wrapping_next_stmt(wi, next_stmt)
    assert consumed == 2
    assert isinstance(with_node, cst.With)
    # body should include the next_stmt (not nested With)
    body = with_node.body
    assert hasattr(body, "body")
    assert len(body.body) == 1
    assert isinstance(body.body[0], cst.SimpleStatementLine)


def test_create_with_wrapping_next_stmt_without_next_statement():
    call = cst.parse_expression("self.assertLogs('x')")
    assert isinstance(call, cst.Call)
    wi = build_with_item_from_assert_call(call)
    assert wi is not None

    with_node, consumed = create_with_wrapping_next_stmt(wi, None)
    assert consumed == 1
    assert isinstance(with_node, cst.With)
    # body should contain a pass statement
    body = with_node.body
    assert hasattr(body, "body")
    assert len(body.body) == 1
    stmt = body.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    assert isinstance(stmt.body[0].value, cst.Name)
    assert stmt.body[0].value.value == "pass"
