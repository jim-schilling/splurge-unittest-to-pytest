import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator_v2 import generator_v2


def _make_collector_output(attrs: dict, teardown: list):
    class_node = cst.ClassDef(name=cst.Name("TestX"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    for k, v in attrs.items():
        ci.setup_assignments[k] = [v]
    ci.teardown_statements = teardown
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestX"] = ci
    return out


def test_typing_names_and_shutil_flag():
    # main_config is a dict literal -> typing should include Dict and Any
    attrs = {
        "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
        "main_config": cst.Dict(elements=[cst.DictElement(key=cst.SimpleString('"k"'), value=cst.SimpleString('"v"'))]),
    }
    teardown = [cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]))])]
    out = _make_collector_output(attrs, teardown)
    res = generator_v2({"collector_output": out})
    names = res.get("needs_typing_names", [])
    assert "Dict" in names or "Any" in names
    # shutil usage should be detected
    assert res.get("needs_shutil_import", False) is True
