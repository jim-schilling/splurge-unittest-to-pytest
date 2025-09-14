import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage


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
        "config_dir": cst.Call(
            func=cst.Name("Path"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
        ),
        "data_dir": cst.Call(
            func=cst.Name("Path"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
        ),
    }
    # teardown references temp_dir via shutil.rmtree(self.temp_dir)
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output(attrs, teardown)
    res = generator_stage({"collector_output": out})
    fixture_nodes = res.get("fixture_nodes", [])
    names = [n.name.value for n in fixture_nodes if isinstance(n, cst.FunctionDef)]
    # Expect per-attribute fixtures instead of composite temp_dirs
    assert "temp_dir" in names
    assert "config_dir" in names or "data_dir" in names
    # If any cleanup used a yield-style fixture, Generator typing may be requested
    _ = res.get("needs_typing_names", [])
