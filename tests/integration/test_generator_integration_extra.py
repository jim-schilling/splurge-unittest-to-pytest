import libcst as cst
from libcst import MetadataWrapper

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator


def test_complex_cleanup_with_conditionals():
    # teardown contains an if that deletes self.x in one branch; generator
    # should still detect cleanup and produce a yield-style fixture.
    src = """
class C:
    def setUp(self):
        self.x = 1

    def tearDown(self):
        if cond:
            del self.x
        else:
            print('no-op')
"""
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
    # If two locals are assigned from the same Call inside setUp, the bundler
    # should create a NamedTuple and a paired fixture.
    src = """
class C:
    def setUp(self):
        a, b = helper()
        self.a = a
        self.b = b

    def tearDown(self):
        pass
"""
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    coll = Collector()
    wrapper.visit(coll)
    out = coll.as_output()

    res = generator({"collector_output": out, "module": module})
    nodes = res.get("fixture_nodes", [])
    # Expect class def (NamedTuple) and a fixture that yields it
    has_namedtuple = any(isinstance(n, cst.ClassDef) and n.name.value.endswith("Data") for n in nodes)
    has_fixture = any(isinstance(n, cst.FunctionDef) and n.name.value.endswith("_data") for n in nodes)
    assert has_namedtuple and has_fixture
