import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage


def make_co(setup):
    co = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    class_node = cst.ClassDef(
        name=cst.Name("ExactTest"), body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])
    )
    ci = ClassInfo(node=class_node)
    ci.setup_assignments = setup
    ci.local_assignments = {}
    ci.teardown_statements = []
    co.classes = {"ExactTest": ci}
    return co


def render(nodes):
    if not nodes:
        return ""
    return cst.Module(body=list(nodes)).code


def test_tuple_literal_emits_tuple_annotation():
    setup = {
        "pair": cst.Tuple(elements=[cst.Element(value=cst.SimpleString('"a"')), cst.Element(value=cst.Integer("1"))])
    }
    co = make_co(setup)
    res = generator_stage({"collector_output": co, "module": cst.Module([])})
    code = render(res.get("fixture_nodes", []))
    # Expect return annotation tuple[str, int]
    assert "-> Tuple[" in code or "-> Tuple[" in code or "Tuple[" in code


def test_list_of_str_emits_list_annotation():
    setup = {"items": cst.List(elements=[cst.Element(value=cst.SimpleString('"x"'))])}
    co = make_co(setup)
    res = generator_stage({"collector_output": co, "module": cst.Module([])})
    code = render(res.get("fixture_nodes", []))
    assert "-> List[" in code or "List[" in code
