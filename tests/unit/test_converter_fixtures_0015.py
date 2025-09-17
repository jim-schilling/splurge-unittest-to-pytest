"""More tests for converter.fixtures to hit fallback and edge branches."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def _first_assign_target_name(fn: cst.FunctionDef) -> str:
    first = fn.body.body[0]
    assign = first.body[0]
    return assign.targets[0].target.value


def test_reserved_name_avoids_collision():
    # attr name 'request' is reserved; ensure binder avoids using it
    call = cst.Call(func=cst.Name("make"), args=[])
    fn = fixtures.create_simple_fixture("request", call)
    # ensure the fixture defines a local binder and does not expose a top-level
    # symbol named 'request' (observable behavior: generated code should not
    # contain an assignment to 'request' at module scope)
    src = cst.Module([]).code_for_node(fn)
    assert "request =" not in src
    assert "_request_value" in src or "return" in src


def test_create_simple_fixture_with_guard_call_wrapped():
    # Call that wraps the attr should be considered self-referential
    call = cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("sql_file"))])
    fn = fixtures.create_simple_fixture_with_guard("sql_file", call)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" in src


def test_create_fixture_for_attribute_fallbacks_when_guard_missing(monkeypatch):
    # Simulate create_simple_fixture_with_guard raising NameError to exercise fallback
    def _raise_name_error(attr_name, value_expr):
        raise NameError("simulated")

    monkeypatch.setattr(fixtures, "create_simple_fixture_with_guard", _raise_name_error)
    fn = fixtures.create_fixture_for_attribute("x", cst.SimpleString("'y'"), {})
    # fallback should produce a simple fixture (returning a literal string)
    # so the returned function should have a Return statement body
    stmts = list(fn.body.body)
    assert any(isinstance(s.body[0], cst.Return) or isinstance(s.body[0], cst.Expr) for s in stmts)
