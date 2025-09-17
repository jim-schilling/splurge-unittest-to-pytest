"""Additional tests for converter.fixtures public helpers."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def _first_stmt_code(fn: cst.FunctionDef) -> str:
    return cst.Module([]).code_for_node(fn.body.body[0])


def test_create_simple_fixture_literal_has_return_annotation():
    fn = fixtures.create_simple_fixture("count", cst.Integer("1"))
    # returns annotation should indicate int
    assert isinstance(fn.returns, cst.Annotation)
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_create_simple_fixture_complex_binds_local_and_returns():
    call = cst.Call(func=cst.Name("compute"), args=[])
    fn = fixtures.create_simple_fixture("value", call)
    src = cst.Module([]).code_for_node(fn)
    # should bind to a local and return it, and include the compute() call
    assert "compute(" in src
    assert "return _value_value" in src


def test_create_fixture_with_cleanup_replaces_attr_references():
    # cleanup statements reference the original attribute name; create_fixture_with_cleanup
    # should bind value to a local and replace references in cleanup with that local name.
    attr = "myattr"
    # cleanup: myattr.close()
    cleanup_stmt = cst.SimpleStatementLine(
        body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Name(attr), attr=cst.Name("close")), args=[]))]
    )
    fn = fixtures.create_fixture_with_cleanup(attr, cst.Call(func=cst.Name("make"), args=[]), [cleanup_stmt])
    src = cst.Module([]).code_for_node(fn)
    # local binder name should be present and original attr name should not appear in cleanup
    assert "_myattr_value" in src
    # ensure cleanup references the local, not the original attr
    assert "myattr.close" not in src


def test_create_autocreated_file_fixture_params_and_body():
    fn = fixtures.create_autocreated_file_fixture(
        "sql_file", content_fixture_name="sql_content", filename="queries.sql"
    )
    src = cst.Module([]).code_for_node(fn)
    # function should accept tmp_path and the content fixture
    assert "tmp_path" in src
    assert "sql_content" in src
    # should joinpath the provided filename and call write_text
    assert "joinpath" in src and "write_text" in src
    # return annotation should be str
    assert isinstance(fn.returns, cst.Annotation)
    assert fn.returns.annotation.value == "str"


def test_create_fixture_for_attribute_prefers_cleanup_when_present():
    # when teardown_cleanup contains statements for the attr, create_fixture_for_attribute
    # should return a fixture that uses the yield-with-cleanup pattern
    attr = "file"
    cleanup_stmt = cst.SimpleStatementLine(
        body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Name(attr), attr=cst.Name("unlink")), args=[]))]
    )
    fn = fixtures.create_fixture_for_attribute(attr, cst.SimpleString("'x'"), {attr: [cleanup_stmt]})
    src = cst.Module([]).code_for_node(fn)
    assert "yield" in src
    assert f"def {attr}(" in src


def test_create_simple_fixture_with_guard_detects_self_referential_subscript():
    # subscript that uses the attr name should be considered self-referential
    expr = cst.Subscript(value=cst.Name("data"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("data")))])
    fn = fixtures.create_simple_fixture_with_guard("data", expr)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" in src
