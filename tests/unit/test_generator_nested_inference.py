import libcst as cst
from splurge_unittest_to_pytest.stages.generator_v2 import generator_v2 as generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def make_collector_out(setup_assignments, local_map=None, teardown_statements=None):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("NestedTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup_assignments
    ci.local_assignments = local_map or {}
    ci.teardown_statements = teardown_statements or []
    co.classes = {"NestedTest": ci}
    return co


def test_infers_nested_list_of_list():
    inner = cst.List(elements=[cst.Element(value=cst.SimpleString('"a"'))])
    outer = cst.List(elements=[cst.Element(value=inner)])
    setup = {"matrix": outer}
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    # expect List and inner List present
    assert "List" in names
    # At least one List name should be present; nested list inference should not error


def test_infers_tuple_of_list():
    inner = cst.List(elements=[cst.Element(value=cst.Integer("1"))])
    tup = cst.Tuple(elements=[cst.Element(value=inner), cst.Element(value=cst.Integer("2"))])
    setup = {"mix": tup}
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    # expect Tuple and List/Any presence
    assert "Tuple" in names or "List" in names
