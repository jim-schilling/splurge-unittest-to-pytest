import libcst as cst
from libcst import MetadataWrapper

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator


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
