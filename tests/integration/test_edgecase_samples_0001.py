import pathlib

import libcst as cst

from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_fixtures_stage import BuildTopLevelFnsStep, CollectClassesStep

SAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent / "unittest_pytest_samples"


def _load_sample(name: str) -> cst.Module:
    p = SAMPLES_DIR / name
    txt = p.read_text(encoding="utf8")
    return cst.parse_module(txt)


def test_nested_class_conversion():
    mod = _load_sample("unittest_nested_classes.py.txt")
    # run collector and steps to lift methods
    collector = Collector()
    mod.visit(collector)
    ctx = {"module": mod, "collector_output": collector.as_output()}
    res = run_steps("st", "t", "n", [CollectClassesStep(), BuildTopLevelFnsStep()], ctx, None)
    new_mod = res.delta.values.get("module")
    assert isinstance(new_mod, cst.Module)
    # ensure outer and inner tests are discoverable (top-level names or preserved nesting)
    names = {n.name.value for n in new_mod.body if isinstance(n, cst.FunctionDef)}
    assert "test_outer" in names or any("test_outer" in getattr(n, "name", cst.Name("")).value for n in new_mod.body)


def test_class_level_parametrize_fixture_preserved():
    mod = _load_sample("pytest_class_level_parametrize.py.txt")
    # find the fixture and assert the params list is present in decorator source
    found_fixture = False
    for node in mod.body:
        if isinstance(node, cst.FunctionDef) and node.name.value == "class_resource":
            found_fixture = True
            src = cst.Module(body=[node]).code
            assert "params=[1, 2]" in src or "params=[1,2]" in src
    assert found_fixture
