import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_fixture_param_detects_temp_dir_name():
    # Build a synthetic CollectorOutput with a class that has a setup assignment
    # where the value expression references `temp_dir` (e.g., Path(temp_dir) used).
    module = cst.parse_module("\n")
    cls_node = cst.parse_module("class TestX:\n    pass\n").body[0]
    cls = ClassInfo(node=cls_node)
    # assign: self.init_api = Path(temp_dir)
    call = cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Name("temp_dir"))])
    # emulate setup_assignments mapping used by collector: attr -> expr
    cls.setup_assignments["init_api_data"] = call
    # no teardown
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": cls})

    context = {"collector_output": out, "module": module, "autocreate": False}
    result = generator_stage(context)
    # result is a dict with module nodes under 'module' after finalize; but generator
    # returns finalized nodes via GeneratorCore.finalize; we can inspect returned mapping
    # The generator_stage returns a dict with keys used by pipeline; inspect 'module' or
    # other keys. For simplicity, inspect context modifications: generator_stage returns
    # a dict, but we can check that the generator produced fixture FunctionDef nodes by
    # calling the generator and inspecting the returned structure's types.
    assert isinstance(result, dict)
    # finalize returns a dict with 'module' key ultimately, but generator returns the
    # output of core.finalize, which places fixtures into 'module'. Verify fixture text
    # contains the expected param name `temp_dir` in a fixture named `init_api_data`.
    # Render produced nodes by constructing a module containing returned 'module' body
    module_node = result.get("module")
    if module_node is None:
        # If finalize returned a dict describing nodes, try to locate fixture nodes
        nodes = result.get("fixture_nodes") or []
        assert nodes, "generator produced no fixture nodes"
        code = cst.Module(body=list(nodes)).code
    else:
        code = module_node.code

    # Expect temp_dir as a parameter in the fixture function signature
    assert "def init_api_data(temp_dir)" in code or "def init_api_data( temp_dir )" in code
