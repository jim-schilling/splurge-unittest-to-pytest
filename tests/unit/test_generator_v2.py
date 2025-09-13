import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator_v2 import generator_v2


def _make_collector_output_for_sample(attrs, teardown_stmts):
    # construct a minimal ClassDef node with an empty body
    class_node = cst.ClassDef(name=cst.Name("TestSample"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    for k, v in attrs.items():
        # store as list with single assigned expr to match collector shape
        ci.setup_assignments[k] = [v]
    ci.teardown_statements = teardown_stmts
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestSample"] = ci
    return out


def test_per_attribute_and_mkdtemp_preserved():
    # attributes including dir-like attrs should produce per-attribute fixtures
    attrs = {
        "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
        "config_dir": cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]),
        "main_config": cst.SimpleString('"ok"'),
    }
    # teardown that rmtree the temp_dir
    teardown = [cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")), args=[cst.Arg(value=cst.Name("temp_dir"))]))])]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator_v2({"collector_output": out})
    # Expect per-attribute fixtures for temp_dir and config_dir and main_config
    names = [n.name.value for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    assert "temp_dir" in names
    assert "config_dir" in names
    assert "main_config" in names
    # ensure mkdtemp call text appears in generated fixture code
    module = cst.Module(body=res["fixture_nodes"])
    code = module.code
    assert "mkdtemp" in code


def test_per_attribute_fixture_when_not_dir_like():
    attrs = {
        "main_config": cst.Dict(elements=[cst.DictElement(key=cst.SimpleString('"k"'), value=cst.SimpleString('"v"'))]),
    }
    out = _make_collector_output_for_sample(attrs, [])
    res = generator_v2({"collector_output": out})
    names = [n.name.value for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    assert "main_config" in names
    # returned fixture for main_config should contain the literal dict
    module = cst.Module(body=res["fixture_nodes"])
    assert "\"k\"" in module.code
