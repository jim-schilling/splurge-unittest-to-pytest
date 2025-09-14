import libcst as cst
from libcst import MetadataWrapper

from splurge_unittest_to_pytest.stages.collector import ClassInfo, CollectorOutput, Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage, generator


def test_generator_stage_basic_fixture_and_shutil_detection():
    # Build a minimal ClassInfo with a single setup assignment and a teardown
    cls_node = cst.ClassDef(name=cst.Name("TestX"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=cls_node)

    # setup_assignments: attr -> [value_expr]
    ci.setup_assignments["config_dir"] = [cst.SimpleString('"/tmp/config"')]

    # teardown_statements referencing shutil (should trigger needs_shutil)
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")), args=[cst.Arg(cst.Name("config_dir"))]
    )
    td_stmt = cst.SimpleStatementLine(body=[cst.Expr(call)])
    ci.teardown_statements.append(td_stmt)

    # Construct CollectorOutput
    module = cst.Module([])
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": ci})

    result = generator_stage({"collector_output": out, "module": module})

    assert isinstance(result, dict)
    assert "fixture_specs" in result
    specs = result["fixture_specs"]
    assert "config_dir" in specs

    # needs_shutil_import should be set because teardown referenced shutil
    assert result.get("needs_shutil_import", False) is True

    # fixture_nodes should include a FunctionDef for the fixture
    nodes = result["fixture_nodes"]
    assert any(isinstance(n, cst.FunctionDef) and n.name.value == "config_dir" for n in nodes)


def test_generator_creates_fixture_from_collector_and_handles_collision():
    # Module with a top-level name that would collide with conventional local
    # name `_a_value` to force binding to a unique local name.
    module = cst.parse_module(
        "_a_value = 99\n\nclass C:\n    def setUp(self):\n        self.a = 1\n\n    def tearDown(self):\n        del self.a\n"
    )

    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()

    ctx = {"collector_output": out, "module": module}
    res = generator(ctx)

    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")

    assert "a" in specs
    spec = specs["a"]
    # Should detect cleanup and mark yield_style True
    assert spec.yield_style is True
    # When module already defines a colliding name, generator should bind to
    # a local whose name includes the conventional base `_a_value`.
    # Verify this by rendering fixture nodes and searching for the conventional
    # local name fragment.
    rendered_all = "\n\n".join(cst.Module(body=[n]).code for n in nodes)
    assert "_a_value" in rendered_all
