import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage


UNIT = """
def init_api_data():
    pass

class TestInitAPI(unittest.TestCase):
    def setUp(self):
        var_a, var_b = get_vals()
        self.var_a = str(var_a)
        self.var_b = str(var_b)

    def tearDown(self):
        cleanup()
"""


def test_fixture_name_avoids_module_collision():
    module = cst.parse_module(UNIT)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    fn_names = [n.name.value for n in nodes if isinstance(n, cst.FunctionDef)]

    # The converter should not emit a fixture named `init_api_data` since
    # a top-level function with that name already exists; it should choose a unique name.
    assert "init_api_data" not in fn_names
    assert any(name.startswith("init_api_data_") for name in fn_names)
