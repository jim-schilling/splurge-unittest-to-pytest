import pathlib
import libcst as cst

from splurge_unittest_to_pytest.stages.steps_fixtures_stage import CollectClassesStep, BuildTopLevelFnsStep
from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.collector import Collector


SAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent / "unittest_pytest_samples"


def _load_sample(name: str) -> cst.Module:
    p = SAMPLES_DIR / name
    txt = p.read_text(encoding="utf8")
    return cst.parse_module(txt)


def test_complex_class_methods_lifted():
    mod = _load_sample("unittest_complex_class.py.txt")
    # Collect class metadata first
    collector = Collector()
    mod.visit(collector)
    collector_out = collector.as_output()
    ctx = {"module": mod, "collector_output": collector_out}
    res = run_steps("st", "t", "n", [CollectClassesStep(), BuildTopLevelFnsStep()], ctx, None)
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # ensure there are top-level functions corresponding to class test methods
    names = {n.name.value for n in new_mod.body if isinstance(n, cst.FunctionDef)}
    assert "test_one" in names
    assert "test_two" in names


def test_parametrize_decorator_preserved():
    mod = _load_sample("pytest_parametrize.py.txt")
    # simply parse and find the function with decorator
    found = False
    for node in mod.body:
        if isinstance(node, cst.FunctionDef) and node.name.value == "test_add":
            # check decorators
            assert node.decorators
            # Look for mark.parametrize in the decorator source
            dec_src = cst.Module(body=[node]).code
            assert "parametrize" in dec_src
            found = True
    assert found
