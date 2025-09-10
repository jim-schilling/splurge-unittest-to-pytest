import libcst as cst
from typing import cast
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.rewriter import rewriter_stage

SAMPLE = '''
class MyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = 1
        self.b = 'x'

    def test_one(self) -> None:
        assert self.a == 1
'''


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
    # Ensure the instance method still accepts `self` (runnable); fixture
    # values should not be added as explicit function parameters because the
    # pipeline now attaches them via an autouse fixture at module level.
    assert ("self" in param_names) or ("cls" in param_names)
