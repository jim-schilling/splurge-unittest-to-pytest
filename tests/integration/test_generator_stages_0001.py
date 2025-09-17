import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import ClassInfo, CollectorOutput, Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage, generator


def test_generator_stage_basic_fixture_and_shutil_detection():
    cls_node = cst.ClassDef(name=cst.Name("TestX"), body=cst.IndentedBlock(body=[]))
    ci = ClassInfo(node=cls_node)
    ci.setup_assignments["config_dir"] = [cst.SimpleString('"/tmp/config"')]
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")), args=[cst.Arg(cst.Name("config_dir"))]
    )
    td_stmt = cst.SimpleStatementLine(body=[cst.Expr(call)])
    ci.teardown_statements.append(td_stmt)
    module = cst.Module([])
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestX": ci})
    result = generator_stage({"collector_output": out, "module": module})
    assert isinstance(result, dict)
    assert "fixture_specs" in result
    specs = result["fixture_specs"]
    assert "config_dir" in specs
    assert result.get("needs_shutil_import", False) is True
    nodes = result["fixture_nodes"]
    assert any((isinstance(n, cst.FunctionDef) and n.name.value == "config_dir" for n in nodes))


def test_generator_creates_fixture_from_collector_and_handles_collision():
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
    assert spec.yield_style is True
    rendered_all = "\n\n".join((cst.Module(body=[n]).code for n in nodes))
    assert "_a_value" in rendered_all


def test_complex_cleanup_with_conditionals():
    src = "\nclass C:\n    def setUp(self):\n        self.x = 1\n\n    def tearDown(self):\n        if cond:\n            del self.x\n        else:\n            print('no-op')\n"
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()
    res = generator({"collector_output": out, "module": module})
    specs = res.get("fixture_specs", {})
    assert "x" in specs
    assert specs["x"].yield_style is True


def test_namedtuple_bundling_from_same_call():
    src = "\nclass C:\n    def setUp(self):\n        a, b = helper()\n        self.a = a\n        self.b = b\n\n    def tearDown(self):\n        pass\n"
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()
    res = generator({"collector_output": out, "module": module})
    nodes = res.get("fixture_nodes", [])
    has_namedtuple = any((isinstance(n, cst.ClassDef) and n.name.value.endswith("Data") for n in nodes))
    has_fixture = any((isinstance(n, cst.FunctionDef) and n.name.value.endswith("_data") for n in nodes))
    assert has_namedtuple and has_fixture


def test_yield_style_cleanup_rewrite():
    src = "\nclass C:\n    def setUp(self):\n        self.x = 42\n\n    def tearDown(self):\n        del self.x\n"
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()
    res = generator({"collector_output": out, "module": module})
    specs = res["fixture_specs"]
    assert "x" in specs
    spec = specs["x"]
    assert spec.yield_style is True


def test_parameterized_fixture_replaces_self_attr_with_param():
    src = "\nclass C:\n    def setUp(self):\n        self.base = '/tmp'\n        self.dir = Path(self.base) / 'cfg'\n\n    def tearDown(self):\n        pass\n\n    def some_test(self):\n        pass\n"
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()
    res = generator({"collector_output": out, "module": module})
    nodes = res.get("fixture_nodes", [])
    found = False
    for n in nodes:
        if isinstance(n, cst.FunctionDef) and n.name.value == "dir":
            found = True
            assert n.params.params
    assert found
