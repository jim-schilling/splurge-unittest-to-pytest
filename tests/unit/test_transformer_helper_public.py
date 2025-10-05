import logging

import libcst as cst

from splurge_unittest_to_pytest.transformers.transformer_helper import (
    ReplacementApplier,
    ReplacementRegistry,
    wrap_small_stmt_if_needed,
)


class PosStub:
    def __init__(self, sline=1, scol=0, eline=1, ecol=1):
        class P:
            pass

        self.start = type("S", (), {"line": sline, "column": scol})
        self.end = type("E", (), {"line": eline, "column": ecol})


def test_replacement_registry_key_and_record_get():
    registry = ReplacementRegistry()
    pos = PosStub(1, 0, 1, 4)
    key = registry.key_from_position(pos)
    assert isinstance(key, tuple) and len(key) == 4

    repl = cst.Integer(value="1")
    registry.record(pos, repl)
    assert registry.get(pos) is repl


def test_replacement_applier_leaves_and_wraps():
    registry = ReplacementRegistry()
    applier = ReplacementApplier(registry)

    # monkeypatch get_metadata on the instance to return our pos
    pos = PosStub(2, 0, 2, 4)
    applier.get_metadata = lambda provider, node: pos

    # Test leave_Call replacement
    call = cst.Call(func=cst.Name("f"))
    repl_expr = cst.Integer(value="2")
    registry.record(pos, repl_expr)
    updated = applier.leave_Call(call, call)
    assert isinstance(updated, cst.BaseExpression)

    # Test leave_SimpleStatementLine replacement wrapping small statement
    # Create a replacement that is a small-statement like Assert
    assert_node = cst.Assert(test=cst.Name("x"))
    # record at same position
    registry.record(pos, assert_node)

    simple = cst.SimpleStatementLine(body=[cst.Expr(call)])
    out = applier.leave_SimpleStatementLine(simple, simple)
    # Result should be a SimpleStatementLine
    assert isinstance(out, cst.BaseStatement)


def test_wrap_small_stmt_if_needed_variants():
    # BaseSmallStatement -> wrapped
    a = cst.Assert(test=cst.Name("ok"))
    wrapped = wrap_small_stmt_if_needed(a)
    assert isinstance(wrapped, cst.SimpleStatementLine)

    # BaseStatement returned as-is
    block = cst.SimpleStatementLine(body=[cst.Pass()])
    assert wrap_small_stmt_if_needed(block) is block

    # BaseExpression wrapped into SimpleStatementLine
    expr = cst.Integer(value="3")
    w2 = wrap_small_stmt_if_needed(expr)
    assert isinstance(w2, cst.SimpleStatementLine)
