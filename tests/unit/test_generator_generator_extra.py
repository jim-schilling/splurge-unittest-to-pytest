import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator import generator_stage


def _make_collector_output(attrs: dict, teardown: list):
    class_node = cst.ClassDef(name=cst.Name("TestDirs"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    for k, v in attrs.items():
        ci.setup_assignments[k] = [v]
    ci.teardown_statements = teardown
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestDirs"] = ci
    return out


def test_temp_dirs_composite_generated():
    # Two dir-like attributes with teardown referencing them -> should synthesize temp_dirs
    attrs = {
        "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
        "config_dir": cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]),
        "data_dir": cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]),
    }
    # teardown references temp_dir via shutil.rmtree(self.temp_dir)
    teardown = [cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]))])]
    out = _make_collector_output(attrs, teardown)
    res = generator_stage({"collector_output": out})
    fixture_nodes = res.get("fixture_nodes", [])
    names = [n.name.value for n in fixture_nodes if isinstance(n, cst.FunctionDef)]
    assert "temp_dirs" in names
    # Ensure the generated temp_dirs fixture is yield-style by checking for Generator annotation
    needs_typing = res.get("needs_typing_names", [])
    assert "Generator" in needs_typing
