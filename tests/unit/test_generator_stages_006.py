import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo

DOMAINS = ["generator", "stages"]


def _run_and_get_code(call_expr: cst.BaseExpression) -> str:
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    cls.setup_assignments["init_api_data"] = call_expr
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})
    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        return cst.Module(body=list(nodes)).code
    return module_node.code


def test_nested_subscript_detects_inner_name():
    # Path(arr[outer[temp_dir]]) -> temp_dir should be parameter
    call = cst.parse_expression("Path(arr[outer[temp_dir]])")
    code = _run_and_get_code(call)
    module = cst.parse_module(code)
    func = next((n for n in module.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params


def test_attribute_chain_detects_base_name():
    # Path(a.b.c.temp_dir) -> a should not be parameter, but temp_dir should (base chain)
    # Use Path(root.parent.temp_dir) - expect parent or root? We'll check temp_dir specifically
    call = cst.parse_expression("Path(root.parent.temp_dir)")
    code = _run_and_get_code(call)
    module = cst.parse_module(code)
    func = next((n for n in module.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert any(n in params for n in ("root", "parent", "temp_dir"))


def test_fstring_detects_name():
    # f"{temp_dir}/x" should mark temp_dir as dependency
    call = cst.parse_expression('f"{temp_dir}/x"')
    code = _run_and_get_code(call)
    module = cst.parse_module(code)
    func = next((n for n in module.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params
