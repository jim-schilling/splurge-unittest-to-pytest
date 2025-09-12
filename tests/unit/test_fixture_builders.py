import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_builders import build_fixtures_from_setup_assignments


def _make_expr_from_code(src: str) -> cst.BaseExpression:
    module = cst.parse_module(src)
    # Expect a single simple statement line with an expression
    node = module.body[0]
    if isinstance(node, cst.SimpleStatementLine):
        # node.body[0] is a BaseSmallStatement; if it's an Expr, return its value
        small = node.body[0]
        if isinstance(small, cst.Expr):
            return small.value
        # Fallback: try parsing a simple assignment RHS
        # mypy: cast to BaseExpression to satisfy return type
        from typing import cast

        return cast(cst.BaseExpression, small)
    raise AssertionError("unexpected node shape")


def test_build_fixtures_with_and_without_cleanup():
    # setup_assignments: one with cleanup, one without
    setup_assignments = {
        "a": _make_expr_from_code("a = 1"),
        "b": _make_expr_from_code("b = compute()"),
    }

    # teardown_cleanup contains cleanup for 'b' only
    cleanup_stmt = cst.parse_statement("del b")
    teardown_cleanup = {"b": [cleanup_stmt]}

    fixtures, needs = build_fixtures_from_setup_assignments(setup_assignments, teardown_cleanup)
    assert needs is True
    assert "a" in fixtures and "b" in fixtures
    # fixtures should be FunctionDef nodes
    assert all(isinstance(fn, cst.FunctionDef) for fn in fixtures.values())
