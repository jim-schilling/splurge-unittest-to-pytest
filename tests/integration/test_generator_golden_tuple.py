import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator as generator_stage
from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


test_unit = """
import unittest

class TestExact(unittest.TestCase):
    def setUp(self):
        self.pair = ("a", 1)

    def test_something(self):
        assert self.pair[1] == 1
"""


def normalize(s: str) -> str:
    # normalize whitespace for golden comparisons
    import re

    s2 = re.sub(r"\s+", " ", s).strip()
    return s2


def test_golden_tuple_fixture_matches_expected(tmp_path, request):
    module = cst.parse_module(test_unit)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module}
    gen_res = generator_stage(ctx)
    nodes = gen_res.get("fixture_nodes", [])
    # build a module containing generator nodes and run import_injector to add typing imports
    generated_module = cst.Module(body=list(nodes))
    inj_ctx = {"module": generated_module, "needs_typing_names": gen_res.get("needs_typing_names", [])}
    inj_res = import_injector_stage(inj_ctx)
    final_mod = inj_res.get("module")
    assert final_mod is not None
    generated_text = final_mod.code
    golden_path = request.config.rootpath / "tests" / "data" / "golden_tuple.expected"
    expected_text = golden_path.read_text(encoding="utf8")
    assert normalize(generated_text) == normalize(expected_text)
