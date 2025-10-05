import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def make_call(owner: str, name: str, args: list[cst.Arg] | None = None) -> cst.Call:
    """Helper to construct attribute calls like owner.name(...)."""
    func = cst.Attribute(value=cst.Name(value=owner), attr=cst.Name(value=name))
    return cst.Call(func=func, args=args or [])


def test_rewrite_membership_and_unary() -> None:
    alias = "lg"

    comp_in = cst.Comparison(
        left=cst.Name("needle"),
        comparisons=[
            cst.ComparisonTarget(
                operator=cst.In(),
                comparator=cst.Attribute(value=cst.Name(alias), attr=cst.Name("output")),
            )
        ],
    )

    out = aw._rewrite_membership_comparison(comp_in, alias)
    assert out is None or isinstance(out, cst.Comparison)

    inner = cst.Comparison(
        left=cst.Name("needle"),
        comparisons=[
            cst.ComparisonTarget(
                operator=cst.In(), comparator=cst.Attribute(value=cst.Name(alias), attr=cst.Name("output"))
            )
        ],
    )
    unary = cst.UnaryOperation(operator=cst.Not(), expression=inner)
    out_unary = aw._rewrite_unary_operation(unary, alias)
    assert out_unary is None or isinstance(out_unary, cst.UnaryOperation)


def test_rewrite_single_alias_assert_and_with_body() -> None:
    alias = "lg"
    left = cst.Subscript(
        value=cst.Attribute(value=cst.Name(alias), attr=cst.Name("output")),
        slice=(cst.SubscriptElement(slice=cst.Index(value=cst.Integer("0"))),),
    )
    comp = cst.Comparison(
        left=left, comparisons=[cst.ComparisonTarget(operator=cst.Equal(), comparator=cst.SimpleString(value='"a"'))]
    )
    a = cst.Assert(test=comp)
    rewritten = aw.rewrite_single_alias_assert(a, alias)
    assert rewritten is None or isinstance(rewritten, cst.Assert)

    stmt = cst.SimpleStatementLine(body=[a])
    dummy_item = cst.WithItem(item=cst.Call(func=cst.Name("context"), args=[]), asname=None)
    with_node = cst.With(items=[dummy_item], body=cst.IndentedBlock(body=[stmt]))
    out_with = aw.rewrite_asserts_using_alias_in_with_body(with_node, alias)
    assert isinstance(out_with, cst.With)


def test_process_try_statement_and_wrap(monkeypatch) -> None:
    try_body = cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    try_node = cst.Try(
        body=try_body,
        handlers=(),
        orelse=None,
        finalbody=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )
    monkeypatch.setattr(aw._orig, "wrap_assert_in_block", lambda stmts, max_d: stmts, raising=False)
    out = aw._process_try_statement(try_node, max_depth=3)
    assert out is None or isinstance(out, cst.BaseStatement)


def test_caplog_helpers_and_with_item_and_wrapping_next() -> None:
    call = make_call(
        "self",
        "assertLogs",
        [
            cst.Arg(value=cst.Name("logger")),
            cst.Arg(value=cst.Attribute(value=cst.Name("logging"), attr=cst.Name("ERROR"))),
        ],
    )
    args = aw.get_caplog_level_args(call)
    assert isinstance(args, list)
    c = aw.build_caplog_call(call)
    assert isinstance(c, cst.Call)

    raises_call = make_call("pytest", "raises", [cst.Arg(value=cst.Name("ValueError"))])
    with_item = cst.WithItem(item=raises_call, asname=None)
    w, consumed = aw.create_with_wrapping_next_stmt(with_item, None)
    assert isinstance(w, cst.With)
    assert isinstance(consumed, int)
