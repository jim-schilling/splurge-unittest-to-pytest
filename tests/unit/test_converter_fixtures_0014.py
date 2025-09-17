"""Additional public-API tests for converter.fixtures to hit more branches."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def _first_assign_target_name(fn: cst.FunctionDef) -> str:
    first = fn.body.body[0]
    assign = first.body[0]
    return assign.targets[0].target.value


def test_create_fixture_with_cleanup_unique_name_on_collision():
    # If cleanup contains the base name, choose_unique_name should append suffix
    cleanup = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("_myattr_value"))])]
    fn = fixtures.create_fixture_with_cleanup("myattr", cst.SimpleString("'x'"), cleanup)

    # Ensure the generated fixture creates a binder (assignment) for the
    # value and that the cleanup expression appears in the generated code.
    class _AssignFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_Assign(self, node: cst.Assign) -> None:
            self.found = True

    finder = _AssignFinder()
    fn.visit(finder)
    assert finder.found, "expected generated fixture to create a binder assignment"
    src = cst.Module([]).code_for_node(fn)
    assert "_myattr_value" in src


def test_infer_primitives_and_containers_return_annotations():
    f_int = fixtures.create_simple_fixture("i", cst.Integer("1"))
    assert f_int.returns is not None and isinstance(f_int.returns.annotation, cst.Name)
    assert f_int.returns.annotation.value == "int"

    f_float = fixtures.create_simple_fixture("f", cst.Float("1.0"))
    assert f_float.returns is not None and isinstance(f_float.returns.annotation, cst.Name)
    assert f_float.returns.annotation.value == "float"

    f_str = fixtures.create_simple_fixture("s", cst.SimpleString("'x'"))
    assert f_str.returns is not None and isinstance(f_str.returns.annotation, cst.Name)
    assert f_str.returns.annotation.value == "str"

    f_tuple = fixtures.create_simple_fixture("t", cst.Tuple(elements=[]))
    assert f_tuple.returns is not None and f_tuple.returns.annotation.value == "Tuple"

    # LibCST requires a set literal to have at least one element
    f_set = fixtures.create_simple_fixture("st", cst.Set(elements=[cst.Element(value=cst.Integer("1"))]))
    assert f_set.returns is not None and f_set.returns.annotation.value == "Set"


def test_create_simple_fixture_with_guard_attribute_self_vs_chain():
    # direct self.attr should be considered self-referential
    expr = cst.Attribute(value=cst.Name("self"), attr=cst.Name("sql_file"))
    fn = fixtures.create_simple_fixture_with_guard("sql_file", expr)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" in src

    # chained attribute like self.x.y should NOT be treated as self-referential
    chain = cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("sql_file"))
    fn2 = fixtures.create_simple_fixture_with_guard("sql_file", chain)
    src2 = cst.Module([]).code_for_node(fn2)
    assert "RuntimeError" not in src2


def test_autocreated_file_fixture_default_filename_and_write_arg():
    # when no filename provided, default is '<attr>.sql' and when no content fixture,
    # write_text should be called with an empty string literal
    fn = fixtures.create_autocreated_file_fixture("myfile")
    # find the write_text call in body statements (second statement)
    stmts = list(fn.body.body)
    # p_assign, write_call, return_stmt
    assert len(stmts) >= 3
    write_stmt = stmts[1]
    # expect Expr(Call(Attribute(p, write_text), args=[SimpleString("''")]))
    expr = write_stmt.body[0]
    assert isinstance(expr, cst.Expr)
    call = expr.value
    assert isinstance(call, cst.Call)
    # the first arg should be a SimpleString with content "''"
    assert call.args and isinstance(call.args[0].value, cst.SimpleString)
    assert "''" in call.args[0].value.value
