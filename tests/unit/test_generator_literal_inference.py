import libcst as cst
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def make_collector_out(setup_assignments, local_map=None, teardown_statements=None):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("LitTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup_assignments
    ci.local_assignments = local_map or {}
    ci.teardown_statements = teardown_statements or []
    co.classes = {"LitTest": ci}
    return co


def render_module_from_nodes(nodes):
    if not nodes:
        return ""
    return cst.Module(body=list(nodes)).code


def test_infers_list_literal_homogeneous_strings():
    setup = {
        "items": cst.List(
            elements=[cst.Element(value=cst.SimpleString('"a"')), cst.Element(value=cst.SimpleString('"b"'))]
        )
    }
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    # typing imports should include List
    names = set(res.get("needs_typing_names", []))
    assert "List" in names
    code = render_module_from_nodes(res.get("fixture_nodes", []))
    # generated fixture should contain the literal list value
    assert '["a", "b"]' in code


def test_infers_tuple_literal_heterogeneous():
    setup = {
        "pair": cst.Tuple(elements=[cst.Element(value=cst.SimpleString('"x"')), cst.Element(value=cst.Integer("1"))])
    }
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    # we expect Tuple or at least List/Any; be conservative
    assert "Tuple" in names or "List" in names or "Any" in names
    code = render_module_from_nodes(res.get("fixture_nodes", []))
    # generated fixture should contain the tuple literal
    assert '("x", 1)' in code


def test_infers_set_literal():
    setup = {"s": cst.Set(elements=[cst.Element(value=cst.Integer("1")), cst.Element(value=cst.Integer("2"))])}
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "List" in names or "Set" in names or "Any" in names


def test_infers_dict_literal():
    # dict literal: {"a": 1}
    key = cst.SimpleString('"a"')
    val = cst.Integer("1")
    pair = cst.DictElement(key=key, value=val)
    setup = {"m": cst.Dict(elements=[pair])}
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "Dict" in names or "Any" in names


def test_infers_list_comprehension_fallbacks_any():
    # [x for x in items] -> comprehension yields ambiguity; expect List or Any in needs_typing_names
    comp = cst.parse_expression("[x for x in items]")
    setup = {"out": comp}
    co = make_collector_out(setup)
    ctx = {"collector_output": co, "module": cst.Module([])}
    res = generator_stage(ctx)
    names = set(res.get("needs_typing_names", []))
    assert "List" in names or "Any" in names
