import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import handle_bare_assert_call


def _stmt(code: str):
    module = cst.parse_module(code)
    return module.body[0]


def test_handle_bare_with_following_statement_wraps():
    stmts = [
        _stmt("self.assertLogs('x', level='INFO')"),
        _stmt("print('hi')"),
    ]

    nodes, consumed, handled = handle_bare_assert_call(stmts, 0)
    assert handled is True
    assert consumed == 2
    assert len(nodes) == 1
    assert isinstance(nodes[0], cst.With)


def test_handle_bare_no_following_statement_creates_pass():
    stmts = [
        _stmt("self.assertLogs('x')"),
    ]

    nodes, consumed, handled = handle_bare_assert_call(stmts, 0)
    assert handled is True
    assert consumed == 1
    assert len(nodes) == 1
    assert isinstance(nodes[0], cst.With)


def test_handle_bare_non_matching_returns_false():
    stmts = [
        _stmt("print('no')"),
    ]

    nodes, consumed, handled = handle_bare_assert_call(stmts, 0)
    assert handled is False
    assert consumed == 0
    assert nodes == []
