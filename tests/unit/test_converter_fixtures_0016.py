"""Additional fixture tests to exercise more branches in converter/fixtures.py"""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def _first_assign_target_name(fn: cst.FunctionDef) -> str:
    first = fn.body.body[0]
    assign = first.body[0]
    return assign.targets[0].target.value


def test_infer_container_annotations():
    li = cst.List(elements=[cst.Element(value=cst.Integer("1"))])
    fn = fixtures.create_simple_fixture("l", li)
    assert fn.returns.annotation.value == "List"

    tup = cst.Tuple(elements=[cst.Element(value=cst.Integer("1"))])
    fn2 = fixtures.create_simple_fixture("t", tup)
    assert fn2.returns.annotation.value == "Tuple"

    st = cst.Set(elements=[cst.Element(value=cst.Integer("1"))])
    fn3 = fixtures.create_simple_fixture("s", st)
    assert fn3.returns.annotation.value == "Set"

    d = cst.Dict(elements=[cst.DictElement(key=cst.SimpleString("'k'"), value=cst.Integer("1"))])
    fn4 = fixtures.create_simple_fixture("d", d)
    assert fn4.returns.annotation.value == "Dict"


def test_infer_float_and_string_annotations():
    f = cst.Float("1.23")
    fn = fixtures.create_simple_fixture("f", f)
    assert fn.returns.annotation.value == "float"

    s = cst.SimpleString("'x'")
    fn2 = fixtures.create_simple_fixture("s", s)
    assert fn2.returns.annotation.value == "str"


def test_choose_unique_name_collision_with_existing_cleanup():
    # create cleanup that already references the base binder name
    attr = "x"
    base_name = f"_{attr}_value"
    # cleanup uses base_name so the creator must pick a unique suffix
    cleanup_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(base_name))])
    fn = fixtures.create_fixture_with_cleanup(attr, cst.Call(func=cst.Name("make"), args=[]), [cleanup_stmt])
    targ = _first_assign_target_name(fn)
    assert targ != base_name
    assert targ.startswith(base_name + "_")


def test_create_simple_fixture_with_guard_attribute_chain_not_self_ref():
    # self.x.y should not be treated as self-referential for attr 'y' because
    # the immediate value is an Attribute whose value is Attribute (not Name)
    expr = cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("y"))
    fn = fixtures.create_simple_fixture_with_guard("y", expr)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" not in src
    # should be a normal fixture (contain a return or assignment)
    assert "return" in src or "=" in src


def test_create_autocreated_file_fixture_defaults():
    # no content fixture name and no filename provided
    fn = fixtures.create_autocreated_file_fixture("myfile")
    src = cst.Module([]).code_for_node(fn)
    # should include tmp_path param only
    assert "tmp_path" in src
    assert "sql_content" not in src
    # default filename should be used
    assert "myfile.sql" in src
    # write_text should be invoked with an empty string literal
    assert "write_text" in src and "''" in src
