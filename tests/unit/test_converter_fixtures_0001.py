"""Tests for `splurge_unittest_to_pytest.converter.fixtures` helpers.

These tests focus on public helper behavior: return annotations for
simple literals, binding behavior for complex values, cleanup name
replacement, guard emission for self-referential placeholders, and
autocreated file fixture shape.
"""

from __future__ import annotations

from splurge_unittest_to_pytest.converter.method_patterns import (
    normalize_method_name,
    is_setup_method,
    is_teardown_method,
    is_test_method,
)
import libcst as cst
from splurge_unittest_to_pytest.converter import fixtures
import pytest
from splurge_unittest_to_pytest.converter import fixture_builders
from tests.unit.helpers.autouse_helpers import make_autouse_attach, insert_attach_fixture_into_module


def test_normalize_camel_to_snake():
    assert normalize_method_name("setUp") == "set_up"
    assert normalize_method_name("tearDown") == "tear_down"
    assert normalize_method_name("shouldDoThing") == "should_do_thing"


def test_is_setup_method_matches_common_names():
    patterns = {"setup", "before_each"}
    assert is_setup_method("setUp", patterns)
    assert is_setup_method("before_each", patterns)
    assert is_setup_method("setup_method", patterns)


def test_is_teardown_method_matches_common_names():
    patterns = {"teardown", "after_each"}
    assert is_teardown_method("tearDown", patterns)
    assert is_teardown_method("after_each", patterns)
    assert is_teardown_method("teardown_method", patterns)


def test_is_test_method_matches_prefixes():
    patterns = {"test_", "should_"}
    assert is_test_method("test_example", patterns)
    assert is_test_method("should_do_it", patterns)
    assert is_test_method("it_handles_case", {"it_"})


def _node_code(node):
    try:
        return node.code
    except Exception:
        return cst.Module([]).code_for_node(node)


def test_create_simple_fixture_literal_annotation():
    fn = fixtures.create_simple_fixture("name", cst.Integer("1"))
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "name"
    assert fn.returns is not None
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_create_simple_fixture_complex_binds_to_local_and_returns():
    call = cst.Call(func=cst.Name("make_value"), args=[])
    fn = fixtures.create_simple_fixture("artifact", call)
    assert fn.name.value == "artifact"
    stmts = list(fn.body.body)
    assert len(stmts) >= 2
    assign = stmts[0]
    ret = stmts[-1]
    targ = assign.body[0].targets[0].target
    assert isinstance(targ, cst.Name)
    bound_name = targ.value
    assert isinstance(ret.body[0].value, cst.Name)
    assert ret.body[0].value.value == bound_name


def test_create_fixture_with_cleanup_replaces_attr_references():
    cleanup = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("myfile"))])]
    val = cst.SimpleString("'content'")
    fn = fixtures.create_fixture_with_cleanup("myfile", val, cleanup)
    first = fn.body.body[0]
    assign = first.body[0]
    bound_name = assign.targets[0].target.value
    has_yield = any(
        (isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0].value, cst.Yield) for s in fn.body.body)
    )
    assert has_yield
    src = _node_code(fn)
    assert bound_name in src
    stmts = list(fn.body.body)
    yield_index = next(
        (
            i
            for i, s in enumerate(stmts)
            if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0].value, cst.Yield)
        )
    )
    cleanup_stmts = stmts[yield_index + 1 :]
    names: set[str] = set()

    class _Collector(cst.CSTVisitor):
        def visit_Name(self, node: cst.Name) -> None:
            names.add(node.value)

    for s in cleanup_stmts:
        s.visit(_Collector())
    assert "myfile" not in names


def test_create_simple_fixture_with_guard_emits_raise_for_self_ref():
    val = cst.Name("sql_file")
    fn = fixtures.create_simple_fixture_with_guard("sql_file", val)
    src = _node_code(fn)
    assert "RuntimeError" in src
    assert "self-referential" in src or "self referential" in src or "ambiguous" in src


def test_create_autocreated_file_fixture_with_and_without_content():
    fn1 = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content", filename="data.sql")
    params = [p.name.value for p in fn1.params.params]
    assert "tmp_path" in params
    assert "sql_content" in params
    assert (
        fn1.returns is not None
        and isinstance(fn1.returns.annotation, cst.Name)
        and (fn1.returns.annotation.value == "str")
    )
    fn2 = fixtures.create_autocreated_file_fixture("sql_file2")
    params2 = [p.name.value for p in fn2.params.params]
    assert "tmp_path" in params2
    assert len(params2) == 1


def test_infer_container_return_annotations():
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
    cleanup = {"foo": [cst.SimpleStatementLine(body=[cst.Pass()])]}
    fn = fixtures.create_fixture_for_attribute("foo", cst.SimpleString("'x'"), cleanup)
    src = _node_code(fn)
    assert "yield" in src or "Yield" in src
    fn2 = fixtures.create_fixture_for_attribute("bar", cst.Name("bar"), {})
    src2 = _node_code(fn2)
    assert "RuntimeError" in src2


def _first_stmt_code(fn: cst.FunctionDef) -> str:
    return cst.Module([]).code_for_node(fn.body.body[0])


def test_create_simple_fixture_literal_has_return_annotation():
    fn = fixtures.create_simple_fixture("count", cst.Integer("1"))
    assert isinstance(fn.returns, cst.Annotation)
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_create_simple_fixture_complex_binds_local_and_returns():
    call = cst.Call(func=cst.Name("compute"), args=[])
    fn = fixtures.create_simple_fixture("value", call)
    src = cst.Module([]).code_for_node(fn)
    assert "compute(" in src
    assert "return _value_value" in src


def test_create_fixture_with_cleanup_replaces_attr_references__01():
    attr = "myattr"
    cleanup_stmt = cst.SimpleStatementLine(
        body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Name(attr), attr=cst.Name("close")), args=[]))]
    )
    fn = fixtures.create_fixture_with_cleanup(attr, cst.Call(func=cst.Name("make"), args=[]), [cleanup_stmt])
    src = cst.Module([]).code_for_node(fn)
    assert "_myattr_value" in src
    assert "myattr.close" not in src


def test_create_autocreated_file_fixture_params_and_body():
    fn = fixtures.create_autocreated_file_fixture(
        "sql_file", content_fixture_name="sql_content", filename="queries.sql"
    )
    src = cst.Module([]).code_for_node(fn)
    assert "tmp_path" in src
    assert "sql_content" in src
    assert "joinpath" in src and "write_text" in src
    assert isinstance(fn.returns, cst.Annotation)
    assert fn.returns.annotation.value == "str"


def test_create_fixture_for_attribute_prefers_cleanup_when_present():
    attr = "file"
    cleanup_stmt = cst.SimpleStatementLine(
        body=[cst.Expr(value=cst.Call(func=cst.Attribute(value=cst.Name(attr), attr=cst.Name("unlink")), args=[]))]
    )
    fn = fixtures.create_fixture_for_attribute(attr, cst.SimpleString("'x'"), {attr: [cleanup_stmt]})
    src = cst.Module([]).code_for_node(fn)
    assert "yield" in src
    assert f"def {attr}(" in src


def test_create_simple_fixture_with_guard_detects_self_referential_subscript():
    expr = cst.Subscript(value=cst.Name("data"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("data")))])
    fn = fixtures.create_simple_fixture_with_guard("data", expr)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" in src


def _first_assign_target_name(fn: cst.FunctionDef) -> str:
    first = fn.body.body[0]
    assign = first.body[0]
    return assign.targets[0].target.value


def test_create_fixture_with_cleanup_unique_name_on_collision():
    cleanup = [cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name("_myattr_value"))])]
    fn = fixtures.create_fixture_with_cleanup("myattr", cst.SimpleString("'x'"), cleanup)

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
    f_set = fixtures.create_simple_fixture("st", cst.Set(elements=[cst.Element(value=cst.Integer("1"))]))
    assert f_set.returns is not None and f_set.returns.annotation.value == "Set"


def test_create_simple_fixture_with_guard_attribute_self_vs_chain():
    expr = cst.Attribute(value=cst.Name("self"), attr=cst.Name("sql_file"))
    fn = fixtures.create_simple_fixture_with_guard("sql_file", expr)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" in src
    chain = cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("sql_file"))
    fn2 = fixtures.create_simple_fixture_with_guard("sql_file", chain)
    src2 = cst.Module([]).code_for_node(fn2)
    assert "RuntimeError" not in src2


def test_autocreated_file_fixture_default_filename_and_write_arg():
    fn = fixtures.create_autocreated_file_fixture("myfile")
    stmts = list(fn.body.body)
    assert len(stmts) >= 3
    write_stmt = stmts[1]
    expr = write_stmt.body[0]
    assert isinstance(expr, cst.Expr)
    call = expr.value
    assert isinstance(call, cst.Call)
    assert call.args and isinstance(call.args[0].value, cst.SimpleString)
    assert "''" in call.args[0].value.value


def _first_assign_target_name__01(fn: cst.FunctionDef) -> str:
    first = fn.body.body[0]
    assign = first.body[0]
    return assign.targets[0].target.value


def test_reserved_name_avoids_collision():
    call = cst.Call(func=cst.Name("make"), args=[])
    fn = fixtures.create_simple_fixture("request", call)
    src = cst.Module([]).code_for_node(fn)
    assert "request =" not in src
    assert "_request_value" in src or "return" in src


def test_create_simple_fixture_with_guard_call_wrapped():
    call = cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("sql_file"))])
    fn = fixtures.create_simple_fixture_with_guard("sql_file", call)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" in src


def test_create_fixture_for_attribute_fallbacks_when_guard_missing(monkeypatch):
    def _raise_name_error(attr_name, value_expr):
        raise NameError("simulated")

    monkeypatch.setattr(fixtures, "create_simple_fixture_with_guard", _raise_name_error)
    fn = fixtures.create_fixture_for_attribute("x", cst.SimpleString("'y'"), {})
    stmts = list(fn.body.body)
    assert any((isinstance(s.body[0], cst.Return) or isinstance(s.body[0], cst.Expr) for s in stmts))


def _first_assign_target_name__02(fn: cst.FunctionDef) -> str:
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
    attr = "x"
    base_name = f"_{attr}_value"
    cleanup_stmt = cst.SimpleStatementLine(body=[cst.Expr(value=cst.Name(base_name))])
    fn = fixtures.create_fixture_with_cleanup(attr, cst.Call(func=cst.Name("make"), args=[]), [cleanup_stmt])
    targ = _first_assign_target_name__02(fn)
    assert targ != base_name
    assert targ.startswith(base_name + "_")


def test_create_simple_fixture_with_guard_attribute_chain_not_self_ref():
    expr = cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("y"))
    fn = fixtures.create_simple_fixture_with_guard("y", expr)
    src = cst.Module([]).code_for_node(fn)
    assert "RuntimeError" not in src
    assert "return" in src or "=" in src


def test_create_autocreated_file_fixture_defaults():
    fn = fixtures.create_autocreated_file_fixture("myfile")
    src = cst.Module([]).code_for_node(fn)
    assert "tmp_path" in src
    assert "sql_content" not in src
    assert "myfile.sql" in src
    assert "write_text" in src and "''" in src


def test_create_fixture_with_cleanup_name_collision():
    attr = "data"
    cleanup_stmt = cst.parse_statement("_data_value = 42")
    fn = fixtures.create_fixture_with_cleanup(attr, cst.SimpleString("'x'"), [cleanup_stmt])
    first = fn.body.body[0]
    assert isinstance(first.body[0], cst.Assign)
    target = first.body[0].targets[0].target
    assert isinstance(target, cst.Name)
    assert target.value.startswith("_data_value_")


@pytest.mark.parametrize(
    "expr,should_guard",
    [
        (cst.Name("amb"), True),
        (cst.Attribute(value=cst.Name("self"), attr=cst.Name("amb")), True),
        (cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("amb"))]), True),
        (cst.Subscript(value=cst.Name("amb"), slice=[cst.SubscriptElement(slice=cst.Index(cst.Integer("1")))]), True),
        (cst.Tuple(elements=[cst.Element(value=cst.Name("amb"))]), True),
        (cst.Call(func=cst.Name("make")), False),
    ],
)
def test_create_simple_fixture_with_guard_variants(expr, should_guard):
    fn = fixtures.create_simple_fixture_with_guard("amb", expr)
    if should_guard:
        assert any((isinstance(s.body[0], cst.Raise) for s in fn.body.body))
    else:
        assert not any((isinstance(s.body[0], cst.Raise) for s in fn.body.body))


def test_create_fixture_for_attribute_fallbacks_to_simple_when_guard_unavailable(monkeypatch):
    def _raise_name_error(*a, **k):
        raise NameError("simulated")

    monkeypatch.setattr(fixtures, "create_simple_fixture_with_guard", _raise_name_error)
    fn = fixtures.create_fixture_for_attribute("nope", cst.Call(func=cst.Name("make")), {})
    assert not any((isinstance(s.body[0], cst.Raise) for s in fn.body.body))
    assert any((isinstance(s.body[0], cst.Return) for s in fn.body.body))


def test_infer_float_and_simple_name_behavior():
    ann = fixtures._infer_simple_return_annotation(cst.Float("1.0"))
    assert isinstance(ann.annotation, cst.Name) and ann.annotation.value == "float"
    fn = fixtures.create_simple_fixture("val", cst.Name("some_name"))
    assert any((isinstance(s.body[0], cst.Return) for s in fn.body.body))
    ret = fn.body.body[0].body[0]
    assert isinstance(ret, cst.Return) and isinstance(ret.value, cst.Name)


def test_create_simple_fixture_with_guard_call_func_equal_attr_triggers_guard():
    expr = cst.Call(func=cst.Name("amb"))
    fn = fixtures.create_simple_fixture_with_guard("amb", expr)
    assert any((isinstance(s.body[0], cst.Raise) for s in fn.body.body))


def test_autocreated_file_fixture_filename_repr_check():
    fn = fixtures.create_autocreated_file_fixture("sql_file", filename="custom.sql")
    assign = fn.body.body[0]
    call = assign.body[0].value
    argval = call.args[0].value
    assert isinstance(argval, cst.SimpleString)
    assert argval.value == repr("custom.sql")


def test_choose_unique_name_collision():
    existing = {"_foo_value", "_foo_value_1", "other"}
    name = fixtures._choose_unique_name("_foo_value", existing)
    assert name == "_foo_value_2"


def test_infer_simple_return_annotation_literals():
    ann = fixtures._infer_simple_return_annotation(cst.Integer("1"))
    assert isinstance(ann, cst.Annotation)
    assert isinstance(ann.annotation, cst.Name)
    assert ann.annotation.value == "int"
    ann = fixtures._infer_simple_return_annotation(cst.SimpleString("'x'"))
    assert ann.annotation.value == "str"


def test_create_simple_fixture_fallback_binds_local(tmp_path):
    call = cst.Call(func=cst.Name("make_value"))
    fn = fixtures.create_simple_fixture("my_fixture", call)
    stmts = list(fn.body.body)
    assert any((isinstance(s.body[0], cst.Assign) for s in stmts))
    assert any((isinstance(s.body[0], cst.Return) for s in stmts))
    assert fn.returns is None


def test_create_simple_fixture_with_guard_self_reference():
    expr = cst.Name("amb")
    fn = fixtures.create_simple_fixture_with_guard("amb", expr)
    assert any((isinstance(s.body[0], cst.Raise) for s in fn.body.body))


def test_create_autocreated_file_fixture_variants():
    fn = fixtures.create_autocreated_file_fixture("sql_file")
    assert len(fn.params.params) == 1
    assert fn.returns is not None and isinstance(fn.returns.annotation, cst.Name)
    fn2 = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content")
    names = [p.name.value for p in fn2.params.params]
    assert "tmp_path" in names and "sql_content" in names
    fn3 = fixtures.create_autocreated_file_fixture("sql_file", filename="custom.sql")
    assign = fn3.body.body[0]
    assert isinstance(assign.body[0], cst.Assign)
    call = assign.body[0].value
    assert isinstance(call, cst.Call)


def test_create_fixture_for_attribute_delegates_to_cleanup_and_guard():
    cleanup_stmt = cst.parse_statement("cleanup()")
    teardown = {"file": [cleanup_stmt]}
    fn = fixtures.create_fixture_for_attribute("file", cst.SimpleString("'x'"), teardown)
    assert any((isinstance(s.body[0], cst.Expr) and isinstance(s.body[0].value, cst.Yield) for s in fn.body.body))
    fn2 = fixtures.create_fixture_for_attribute("amb", cst.Name("amb"), {})
    assert any((isinstance(s.body[0], cst.Raise) for s in fn2.body.body))


def test_create_simple_fixture_simple_literal_annotation_and_return():
    fn = fixtures.create_simple_fixture("num", cst.Integer("1"))
    first = fn.body.body[0]
    assert isinstance(first.body[0], cst.Return)
    assert isinstance(first.body[0].value, cst.Integer)
    assert isinstance(fn.returns, cst.Annotation)
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_create_fixture_with_cleanup_replaces_attr_name_in_cleanup():
    attr = "data"
    cleanup_stmt = cst.parse_statement("do_cleanup(data)")
    fn = fixtures.create_fixture_with_cleanup(attr, cst.SimpleString("'x'"), [cleanup_stmt])
    calls = [s for s in fn.body.body if isinstance(s.body[0], cst.Expr) and isinstance(s.body[0].value, cst.Call)]
    assert calls, "expected a cleanup call in fixture body"
    call = calls[-1].body[0].value
    arg0 = call.args[0].value
    assert isinstance(arg0, cst.Name)
    assert arg0.value.startswith("_data_value")


def test_create_autocreated_file_fixture_write_args_inspected():
    fn = fixtures.create_autocreated_file_fixture("sql_file")
    write_stmt = fn.body.body[1]
    assert isinstance(write_stmt.body[0], cst.Expr)
    write_call = write_stmt.body[0].value
    assert isinstance(write_call.args[0].value, cst.SimpleString)
    assert write_call.args[0].value.value == "''"
    fn2 = fixtures.create_autocreated_file_fixture("sql_file", content_fixture_name="sql_content")
    write_stmt2 = fn2.body.body[1]
    write_call2 = write_stmt2.body[0].value
    assert isinstance(write_call2.args[0].value, cst.Name)
    assert write_call2.args[0].value.value == "sql_content"


def test_collect_identifiers_from_statements_and_choose_unique_name_no_collision():
    stmts = [cst.parse_statement("a = 1"), cst.parse_statement("b = 2")]
    ids = fixtures._collect_identifiers_from_statements(stmts)
    assert "a" in ids and "b" in ids
    name = fixtures._choose_unique_name("_new_value", ids)
    assert name == "_new_value"


def test_infer_simple_return_annotation_containers():
    ann = fixtures._infer_simple_return_annotation(cst.List([]))
    assert isinstance(ann.annotation, cst.Name) and ann.annotation.value == "List"
    ann = fixtures._infer_simple_return_annotation(cst.Tuple([]))
    assert ann.annotation.value == "Tuple"
    ann = fixtures._infer_simple_return_annotation(cst.Set([cst.Element(value=cst.Integer("1"))]))
    assert ann.annotation.value == "Set"
    ann = fixtures._infer_simple_return_annotation(
        cst.Dict([cst.DictElement(key=cst.SimpleString("'k'"), value=cst.Integer("1"))])
    )
    assert ann.annotation.value == "Dict"


def test_attribute_chain_does_not_trigger_guard():
    expr = cst.Attribute(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("x")), attr=cst.Name("y"))
    fn = fixtures.create_simple_fixture_with_guard("y", expr)
    assert not any((isinstance(s.body[0], cst.Raise) for s in fn.body.body))


def test_infer_none_and_collect_identifiers_handles_bad_stmt():
    assert fixtures._infer_simple_return_annotation(None) is None
    bad = object()
    ids = fixtures._collect_identifiers_from_statements([bad, cst.parse_statement("z = 1")])
    assert "z" in ids


def test_is_self_referential_subscript_index_hits_true():
    sub = cst.Subscript(value=cst.Name("amb"), slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Name("amb")))])
    assert fixtures._is_self_referential(sub, "amb")


def test_create_simple_fixture_none_fallback():
    fn = fixtures.create_simple_fixture("noney", None)
    assert any((isinstance(s.body[0], cst.Assign) for s in fn.body.body))
    assert any((isinstance(s.body[0], cst.Return) for s in fn.body.body))


def test_build_fixtures_from_setup_assignments_creates_simple_and_cleanup():
    setup = {"a": cst.parse_expression("1"), "b": cst.parse_expression("2")}
    teardown = {"a": [cst.parse_statement("cleanup(self.a)")]}
    fixtures_map, needs_pytest = fixture_builders.build_fixtures_from_setup_assignments(setup, teardown)
    assert needs_pytest is True
    assert "a" in fixtures_map and "b" in fixtures_map
    a_code = cst.Module(body=[fixtures_map["a"]]).code
    b_code = cst.Module(body=[fixtures_map["b"]]).code
    assert "yield _a_value" in a_code
    assert "return _b_value" in b_code or "return 2" in b_code


def test_create_simple_fixture_structure_and_decorator():
    fd = fixtures.create_simple_fixture("my_fixture", cst.parse_expression("42"))
    code = cst.Module(body=[fd]).code
    assert isinstance(fd, cst.FunctionDef)
    assert fd.name.value == "my_fixture"
    if "_my_fixture_value" in code:
        assert "return _my_fixture_value" in code
    else:
        assert "return 42" in code
    assert "pytest.fixture" in code


def test_create_fixture_with_cleanup_replaces_names_and_yields():
    cleanup_stmt = cst.parse_statement("cleanup(self.x)")
    fd = fixtures.create_fixture_with_cleanup("x", cst.parse_expression("1"), [cleanup_stmt])
    code = cst.Module(body=[fd]).code
    assert isinstance(fd, cst.FunctionDef)
    assert "yield _x_value" in code
    assert "_x_value" in code and "self.x" not in code


def test_make_autouse_attach_to_instance_fixture_builds_setters():
    foo_fd = fixtures.create_simple_fixture("foo", cst.parse_expression("1"))
    module_fn = make_autouse_attach({"foo": foo_fd})
    code = cst.Module(body=[module_fn]).code
    assert isinstance(module_fn, cst.FunctionDef)
    assert module_fn.name.value == "_attach_to_instance"
    assert "getattr" in code
    assert "setattr" in code
    assert "autouse" in code and "True" in code


def test_add_autouse_attach_fixture_to_module_inserts_after_pytest_import():
    mod = cst.parse_module("import pytest\n")
    foo_fd = fixtures.create_simple_fixture("bar", cst.parse_expression("2"))
    new_mod = insert_attach_fixture_into_module(mod, make_autouse_attach({"bar": foo_fd}))
    code = new_mod.code
    assert "import pytest" in code
    assert "_attach_to_instance" in code
    assert code.find("import pytest") < code.find("_attach_to_instance")


def test_create_fixture_for_attribute_dispatches_to_cleanup_or_simple():
    td = {"a": [cst.parse_statement("cleanup(self.a)")]}
    fd1 = fixtures.create_fixture_for_attribute("a", cst.parse_expression("0"), td)
    assert "yield _a_value" in cst.Module(body=[fd1]).code
    fd2 = fixtures.create_fixture_for_attribute("b", cst.parse_expression("0"), {})
    code2 = cst.Module(body=[fd2]).code
    assert "return _b_value" in code2 or "return 0" in code2
