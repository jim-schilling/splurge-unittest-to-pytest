import libcst as cst

from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator
from splurge_unittest_to_pytest.stages.manager import StageManager


def test_build_pytest_fixture_no_kwargs():
    dec = build_pytest_fixture_decorator(None)
    assert isinstance(dec, cst.Decorator)
    assert isinstance(dec.decorator, cst.Attribute)


def test_build_pytest_fixture_with_kwargs():
    dec = build_pytest_fixture_decorator({"autouse": True})
    assert isinstance(dec, cst.Decorator)
    assert isinstance(dec.decorator, cst.Call)


def test_stage_manager_register_run_dump():
    mgr = StageManager()

    def sample_stage(ctx):
        return {"ok": True}

    mgr.register(sample_stage)
    res = mgr.run(cst.Module([]))
    assert isinstance(res, dict)
    assert "ok" in res
