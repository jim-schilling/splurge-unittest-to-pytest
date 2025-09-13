import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator_v2 import generator_v2 as generator_stage


UNIT = """
class TestThing(unittest.TestCase):
    def setUp(self):
        a, b = make_pair()
        self.a = a
        self.b = b

    def test_ok(self):
        assert self.a is not None
"""


def test_composite_without_teardown_emits_returning_fixture():
    module = cst.parse_module(UNIT)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    result = generator_stage(ctx)
    nodes = result.get("fixture_nodes", [])
    # Should contain a fixture that returns (non-yield) the container
    has_return_fixture = any(
        isinstance(n, cst.FunctionDef)
        and any(isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Return) for s in n.body.body)
        for n in nodes
    )
    assert has_return_fixture
