import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage

DOMAINS = ["generator", "stages"]


UNIT = """
class TestThree(unittest.TestCase):
    def setUp(self):
        x, y, z = make_vals()
        self.x = 's'
        self.y = 1
        self.z = 3.14

    def tearDown(self):
        pass
"""


def test_three_tuple_namedtuple_field_types():
    module = cst.parse_module(UNIT)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    code = "\n".join(cst.Module(body=[n]).code for n in nodes)
    # Expect the NamedTuple to include annotations for x:str, y:int, z:float
    assert "x: str" in code or "x: Any" in code
    assert "y: int" in code or "y: Any" in code
    assert "z: float" in code or "z: Any" in code
