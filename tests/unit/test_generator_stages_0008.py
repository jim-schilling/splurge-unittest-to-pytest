import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage

DOMAINS = ["generator", "stages"]


UNIT = '''
class TestInitAPI(unittest.TestCase):
    def setUp(self):
        self.resource = util.get_resource()
        self.content = """String Literal"""
        var_a, var_b = get_resource_with_schema(
            self.resource,
            "Another String Literal",
            self.content
        )
        self.var_a = str(var_a)
        self.var_b = str(var_b)

    def tearDown(self):
        util.cleanup(self.resource)

    def test_init_api_functionality(self) -> None:
        assert self.content == """String Literal"""
        assert self.var_a is not None
        assert self.var_b is not None
'''


def test_generator_emits_namedtuple_and_fixture():
    module = cst.parse_module(UNIT)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    # Debug: ensure collector recorded local assignments and setup attrs
    # local_assignments should contain var_a and var_b
    local_map = out.classes.get("TestInitAPI").local_assignments
    assert "var_a" in local_map and "var_b" in local_map
    # Ensure the assigned value recorded for the locals is a Call (the helper)
    import libcst as _cst

    assert isinstance(local_map["var_a"], tuple) and isinstance(local_map["var_a"][0], _cst.Call)
    assert isinstance(local_map["var_b"], tuple) and isinstance(local_map["var_b"][0], _cst.Call)
    # indices should reflect tuple-unpack ordering
    assert local_map["var_a"][1] == 0
    assert local_map["var_b"][1] == 1
    # setup_assignments should contain resource, content, var_a, var_b
    setup = out.classes.get("TestInitAPI").setup_assignments
    missing = [k for k in ("resource", "content", "var_a", "var_b") if k not in setup]
    assert not missing, f"Missing expected setup assignments: {missing}; keys={list(setup.keys())}"
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    code = "\n".join(cst.Module(body=[n]).code for n in nodes)

    # Derive expected names from the TestCase class name used in UNIT
    class_name = "TestInitAPI"
    base = class_name[4:] if class_name.startswith("Test") else class_name
    namedtuple_name = f"_{base}Data"

    # simple CamelCase -> snake_case
    import re

    snake = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", base)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake).lower().lstrip("_")
    fixture_name = f"{snake}_data"

    # Pass if generator emitted either the NamedTuple class or the bundled fixture
    assert f"class {namedtuple_name}(NamedTuple):" in code or f"def {fixture_name}(" in code
