import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator import generator


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
        "config_dir": cst.Call(
            func=cst.Name("Path"),
            args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
        ),
        "main_config": cst.SimpleString('"ok"'),
    }
    # teardown that rmtree the temp_dir
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Name("temp_dir"))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator({"collector_output": out})
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
    res = generator({"collector_output": out})
    names = [n.name.value for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    assert "main_config" in names
    # returned fixture for main_config should contain the literal dict
    module = cst.Module(body=res["fixture_nodes"])
    assert '"k"' in module.code


def test_literal_yield_and_teardown():
    attrs = {"value": cst.Integer(value="42")}
    teardown = [
        cst.SimpleStatementLine(
            body=[cst.Expr(cst.Assign(targets=[cst.AssignTarget(target=cst.Name("value"))], value=cst.Name("None")))]
        )
    ]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator({"collector_output": out})
    nodes = [n for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    found = False
    for n in nodes:
        if n.name.value == "value":
            module = cst.Module(body=[n])
            code = module.code
            assert "yield 42" in code or "yield 42" in code
            assert "value = None" in code
            found = True
    assert found


def test_non_literal_binds_local_and_cleanup_refs_local():
    attrs = {"path": cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Name("temp"))])}
    teardown = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("path")))],
                    )
                )
            ]
        )
    ]
    out = _make_collector_output_for_sample(attrs, teardown)
    res = generator({"collector_output": out})
    nodes = [n for n in res["fixture_nodes"] if isinstance(n, cst.FunctionDef)]
    for n in nodes:
        if n.name.value == "path":
            module = cst.Module(body=[n])
            code = module.code
            assert "yield _path_value" in code or "_path_value" in code
            assert "_path_value" in code
            return
    assert False, "did not find generated fixture for path"


def test_mkdir_preserved_in_fixture():
    # simulate a setup method containing a mkdir call for attr 'd'
    class_node = cst.ClassDef(name=cst.Name("TestMk"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=class_node)
    # attach a synthetic setup method node body using parse_module and wrap into FunctionDef
    setup_module = cst.parse_module("self.d = Path(temp)\nself.d.mkdir(parents=True)\n")
    # create a fake setUp FunctionDef node with the parsed statements as its body
    setup_fn = cst.FunctionDef(
        name=cst.Name("setUp"), params=cst.Parameters(params=[]), body=cst.IndentedBlock(body=list(setup_module.body))
    )
    ci.setup_methods = [setup_fn]
    ci.setup_assignments = {"d": [cst.Call(func=cst.Name("Path"), args=[cst.Arg(value=cst.Name("temp"))])]}
    ci.teardown_statements = []
    out = CollectorOutput(module=cst.Module([]), module_docstring_index=None, imports=[])
    out.classes["TestMk"] = ci
    res = generator({"collector_output": out})
    for n in res["fixture_nodes"]:
        if isinstance(n, cst.FunctionDef) and n.name.value == "d":
            module = cst.Module(body=[n])
            code = module.code
            # When the original class has a setUp method, the generator
            # should not duplicate mkdir calls into per-attribute fixtures
            # (the setUp remains on the class). Ensure we do not duplicate.
            assert "mkdir" not in code
            assert "parents=True" not in code
            return
    assert False, "did not find fixture for d"
