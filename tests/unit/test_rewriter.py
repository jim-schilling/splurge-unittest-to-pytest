import libcst as cst
from typing import cast
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.rewriter import rewriter_stage

SAMPLE = """
class MyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = 1
        self.b = 'x'

    def test_one(self) -> None:
        assert self.a == 1
"""


def test_rewriter_adds_fixture_params_and_removes_self() -> None:
    module = cst.parse_module(SAMPLE)
    # collect
    visitor = Collector()
    module.visit(visitor)
    co = visitor.as_output()
    ctx = {"module": module, "collector_output": co}
    res = rewriter_stage(ctx)
    new_mod = cast(cst.Module, res.get("module"))
    # find test function
    cls = [n for n in new_mod.body if isinstance(n, cst.ClassDef) and n.name.value == "MyTests"][0]
    func = [m for m in cls.body.body if isinstance(m, cst.FunctionDef) and m.name.value == "test_one"][0]
    param_names = [p.name.value for p in func.params.params]
    # After rewriter, leading 'self' should be removed and fixtures 'a' and 'b'
    # (from setUp assignments) should be appended as parameters.
    assert "self" not in param_names and "cls" not in param_names
    assert "a" in param_names and "b" in param_names
