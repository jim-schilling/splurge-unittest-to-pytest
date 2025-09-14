import libcst as cst
from libcst import MetadataWrapper

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator


def test_yield_style_cleanup_rewrite():
    # Setup where setUp assigns self.x and tearDown deletes it, expecting a
    # yield-style fixture that rewrites cleanup to use the fixture name.
    src = """
class C:
    def setUp(self):
        self.x = 42

    def tearDown(self):
        del self.x
"""
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
    # setUp assigns an attribute based on a helper local; returned fixture
    # should accept a param replacing self.attr usage.
    src = """
class C:
    def setUp(self):
        self.base = '/tmp'
        self.dir = Path(self.base) / 'cfg'

    def tearDown(self):
        pass

    def some_test(self):
        pass
"""
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()

    res = generator({"collector_output": out, "module": module})
    nodes = res.get("fixture_nodes", [])
    # find fixture def for 'dir' and ensure it has params when non-literal
    found = False
    for n in nodes:
        if isinstance(n, cst.FunctionDef) and n.name.value == "dir":
            found = True
            assert n.params.params  # should have at least one parameter
    assert found
