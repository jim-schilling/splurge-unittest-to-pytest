import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_fixture_param_detects_temp_dir_attr():
    # Path(temp_dir.attr) -> temp_dir should be a parameter
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    # call: Path(temp_dir.attr)
    call = cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("temp_dir"), attr=cst.Name("attr")))])
    cls.setup_assignments["init_api_data"] = call
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})

    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    assert isinstance(result, dict)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        module_code = cst.Module(body=list(nodes))
    else:
        module_code = module_node
    func = next((n for n in module_code.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params


def test_fixture_param_detects_temp_dir_subscript():
    # Path(arr[temp_dir]) -> temp_dir should be a parameter
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    # call: Path(arr[temp_dir]) - construct via parsing to avoid libcst constructor differences
    call = cst.parse_expression("Path(arr[temp_dir])")
    # parse_expression returns a Call node; use it directly
    cls.setup_assignments["init_api_data"] = call
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})

    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    assert isinstance(result, dict)
    module_node = result.get("module")
    if module_node is None:
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        module_code = cst.Module(body=list(nodes))
    else:
        module_code = module_node
    func = next((n for n in module_code.body if isinstance(n, cst.FunctionDef) and n.name.value == "init_api_data"), None)
    assert func is not None
    params = [p.name.value for p in func.params.params]
    assert "temp_dir" in params
