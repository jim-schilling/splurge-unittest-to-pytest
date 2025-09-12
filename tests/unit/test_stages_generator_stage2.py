import libcst as cst

from splurge_unittest_to_pytest.stages import generator
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def _make_collector_output(module: cst.Module, cls_info: ClassInfo) -> CollectorOutput:
    return CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=True)


def test_multi_assigned_forces_binding_and_local_assignment():
    # multi-assigned: two assignments -> prefer binding to local_name
    module = cst.parse_module("x = 0\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    # two assignments for attribute 'x'
    cls_info.setup_assignments = {"x": [cst.Integer("1"), cst.Integer("2")]}
    # simple cleanup referencing self.x
    cleanup = cst.parse_statement("self.x = None")
    cls_info.teardown_statements = [cleanup]

    out = _make_collector_output(module, cls_info)
    res = generator.generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")
    assert "x" in specs
    # fixture should have local_value_name set and node should include assignment to it
    local = specs["x"].local_value_name
    assert local is not None and local.startswith("_x_value")
    # Render nodes and assert assign to local and yield of local present
    rendered = "\n\n".join(cst.Module(body=[n]).code for n in nodes)
    assert f"{local} =" in rendered
    assert f"yield {local}" in rendered


def test_literal_yield_without_module_collision_rewrites_cleanup_to_fixture_name():
    # literal value + simple cleanup + no module underscores -> yield literal and cleanup rewritten to fixture name
    module = cst.parse_module("a = 0\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("5")]}
    cls_info.teardown_statements = [cst.parse_statement("self.a = None")]

    out = _make_collector_output(module, cls_info)
    res = generator.generator_stage({"collector_output": out, "module": module})
    nodes = res.get("fixture_nodes")
    assert nodes, "expected fixture node for 'a'"
    rendered = cst.Module(body=[nodes[0]]).code
    # Should yield the literal directly
    assert "yield 5" in rendered
    # Cleanup should be rewritten to use fixture name (a = None)
    assert "a = None" in rendered


def test_module_collision_forces_binding_even_for_literal():
    # If module already defines _a_value or contains underscore-prefixed names, force binding
    module = cst.parse_module("_a_value = 1\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("7")]}
    cls_info.teardown_statements = [cst.parse_statement("self.a = None")]

    out = _make_collector_output(module, cls_info)
    res = generator.generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")
    assert "a" in specs
    local = specs["a"].local_value_name
    assert local is not None and local.startswith("_a_value")
    # rendered node should include assignment to local and yield local
    rendered = cst.Module(body=[nodes[0]]).code
    assert f"{local} =" in rendered
    assert f"yield {local}" in rendered
    # cleanup should reference the local name
    assert f"{local} = None" in rendered


def test_name_collision_skips_fixture_node_creation_but_records_spec():
    # If a top-level function with same name exists, generator records spec but does not create a fixture node
    module = cst.parse_module("def a():\n    pass\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    cls_info.setup_assignments = {"a": [cst.Integer("9")]}
    cls_info.teardown_statements = []

    out = _make_collector_output(module, cls_info)
    res = generator.generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")
    assert "a" in specs
    # fixture_nodes should not contain a FunctionDef named 'a'
    assert not any(isinstance(n, cst.FunctionDef) and n.name.value == "a" for n in nodes)
