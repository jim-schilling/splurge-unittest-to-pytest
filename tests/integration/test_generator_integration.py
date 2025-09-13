import libcst as cst
from libcst import MetadataWrapper

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages import generator


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
    res = generator.generator_stage(ctx)

    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")

    assert "a" in specs
    spec = specs["a"]
    # Should detect cleanup and mark yield_style True
    assert spec.yield_style is True
    # local_value_name should be set and different from conventional base if collision
    assert spec.local_value_name is not None
    assert nodes and any(n.name.value == "a" for n in nodes)
