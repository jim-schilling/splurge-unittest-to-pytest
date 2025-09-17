"""Tests for `splurge_unittest_to_pytest.converter.fixtures` helpers.

These tests focus on public helper behavior: return annotations for
simple literals, binding behavior for complex values, cleanup name
replacement, guard emission for self-referential placeholders, and
autocreated file fixture shape.
"""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def _node_code(node):
    # FunctionDef nodes don't expose .code; use a temporary Module to
    # generate source for the node.
    try:
        return node.code
    except Exception:
        return cst.Module([]).code_for_node(node)


def test_create_simple_fixture_literal_annotation():
    fn = fixtures.create_simple_fixture("name", cst.Integer("1"))
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "name"
    # returns should be an annotation pointing to int
    assert fn.returns is not None
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_create_simple_fixture_complex_binds_to_local_and_returns():
    # complex value: Call expression should result in a bound local and return of that name
    call = cst.Call(func=cst.Name("make_value"), args=[])
    fn = fixtures.create_simple_fixture("artifact", call)
    assert fn.name.value == "artifact"
    # body should have an Assign then a Return
    stmts = list(fn.body.body)
    assert len(stmts) >= 2
    assign = stmts[0]
    ret = stmts[-1]
    # assign target should be a Name like _artifact_value or with suffix
    targ = assign.body[0].targets[0].target
    assert isinstance(targ, cst.Name)
    bound_name = targ.value
    # return should return that bound name
    assert isinstance(ret.body[0].value, cst.Name)
    assert ret.body[0].value.value == bound_name


def test_create_fixture_with_cleanup_replaces_attr_references():
    # cleanup_statements reference the original attr name; after fixture creation
    # they should reference the internal bound variable instead.
    cleanup = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])]
    val = cst.SimpleString("'content'")
    fn = fixtures.create_fixture_with_cleanup("myfile", val, cleanup)
    # find the assigned name from first body stmt
    first = fn.body.body[0]
    assign = first.body[0]
    bound_name = assign.targets[0].target.value
    # ensure yield present
    has_yield = any(
        isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0].value, cst.Yield) for s in fn.body.body
    )
    assert has_yield
    # cleanup statements (later in body) should reference bound_name not original attr
    src = _node_code(fn)
    assert bound_name in src
    # cleanup statements (after the yield) should not reference the original attr
    stmts = list(fn.body.body)
    # find the index of the yield statement
    yield_index = next(
        i
        for i, s in enumerate(stmts)
        if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0].value, cst.Yield)
    )
    cleanup_stmts = stmts[yield_index + 1 :]

    # collect Name identifiers used in cleanup statements
    names: set[str] = set()

    class _Collector(cst.CSTVisitor):
        def visit_Name(self, node: cst.Name) -> None:
            names.add(node.value)

    for s in cleanup_stmts:
        s.visit(_Collector())

    assert "myfile" not in names


def test_create_simple_fixture_with_guard_emits_raise_for_self_ref():
    # value_expr that is a name equal to the attr should be considered self-referential
    val = cst.Name("sql_file")
    fn = fixtures.create_simple_fixture_with_guard("sql_file", val)
    src = _node_code(fn)
    assert "RuntimeError" in src
    assert "self-referential" in src or "self referential" in src or "ambiguous" in src


def test_create_autocreated_file_fixture_with_and_without_content():
    fn1 = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content", filename="data.sql")
    # should have tmp_path param and content param
    params = [p.name.value for p in fn1.params.params]
    assert "tmp_path" in params
    assert "sql_content" in params
    assert (
        fn1.returns is not None
        and isinstance(fn1.returns.annotation, cst.Name)
        and fn1.returns.annotation.value == "str"
    )

    fn2 = fixtures.create_autocreated_file_fixture("sql_file2")
    params2 = [p.name.value for p in fn2.params.params]
    assert "tmp_path" in params2
    # when no content fixture, only tmp_path param should exist
    assert len(params2) == 1


def test_infer_container_return_annotations():
    # List and Dict literals should produce typing-style annotations
    fn_list = fixtures.create_simple_fixture("lst", cst.List(elements=[]))
    assert fn_list.returns is not None and isinstance(fn_list.returns.annotation, cst.Name)
    assert fn_list.returns.annotation.value == "List"

    fn_dict = fixtures.create_simple_fixture("dct", cst.Dict(elements=[]))
    assert fn_dict.returns is not None and isinstance(fn_dict.returns.annotation, cst.Name)
    assert fn_dict.returns.annotation.value == "Dict"


def test_autocreated_file_fixture_calls_write_text():
    fn = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content", filename="f.sql")
    found = False

    class _Finder(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:
            nonlocal found
            if isinstance(node.attr, cst.Name) and node.attr.value == "write_text":
                found = True

    fn.visit(_Finder())
    assert found


def test_create_fixture_for_attribute_delegates_to_cleanup_or_guard():
    # when teardown_cleanup has entries, a yield-based fixture should be returned
    cleanup = {"foo": [cst.SimpleStatementLine(body=[cst.Pass()])]}  # presence is enough
    fn = fixtures.create_fixture_for_attribute("foo", cst.SimpleString("'x'"), cleanup)
    src = _node_code(fn)
    assert "yield" in src or "Yield" in src

    # when no cleanup and value is self-referential, guard is used
    fn2 = fixtures.create_fixture_for_attribute("bar", cst.Name("bar"), {})
    src2 = _node_code(fn2)
    assert "RuntimeError" in src2
