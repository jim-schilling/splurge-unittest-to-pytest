from splurge_unittest_to_pytest.degradation import DegradationManager, TransformationTier
from splurge_unittest_to_pytest.result import Result


class DummyConfig:
    def __init__(self, enabled=True, tier="advanced"):
        self.degradation_enabled = enabled
        self.degradation_tier = tier


def success_transform(*args, **kwargs):
    return Result.success("ok")


def failing_transform(*args, **kwargs):
    raise RuntimeError("boom")


def failing_result_transform(*args, **kwargs):
    return Result.failure(RuntimeError("fail"))


def test_degradation_skips_when_disabled():
    mgr = DegradationManager(enabled=False)
    cfg = DummyConfig(enabled=False)
    res = mgr.degrade_transformation("assert_check", success_transform, cfg)
    assert not res.degradation_applied
    assert res.original_result.is_success()


def test_degradation_handles_exception_and_applies_essential():
    mgr = DegradationManager(enabled=True)
    cfg = DummyConfig(enabled=True, tier="essential")
    # failing_transform raises, essential tier should produce a fallback
    dr = mgr.degrade_transformation(
        "assert_complex",
        failing_transform,
        cfg,
    )
    assert dr.failures
    assert dr.recovery_attempts >= 1
    assert isinstance(dr.degraded_result, Result)


def test_advanced_and_experimental_paths_return_degraded_results():
    mgr = DegradationManager(enabled=True)
    cfg_adv = DummyConfig(enabled=True, tier="advanced")
    dr_adv = mgr.degrade_transformation("parametrize", failing_result_transform, cfg_adv)
    assert dr_adv.failures

    cfg_exp = DummyConfig(enabled=True, tier="experimental")
    dr_exp = mgr.degrade_transformation("fixture_complex", failing_result_transform, cfg_exp)
    assert dr_exp.failures


def test_get_failure_summary_and_reset():
    mgr = DegradationManager(enabled=True)
    cfg = DummyConfig(enabled=True, tier="essential")
    mgr.degrade_transformation("assert_check", failing_result_transform, cfg)
    summary = mgr.get_failure_summary()
    assert summary["total_failures"] == 1
    assert "essential" in summary["failures_by_tier"]
    mgr.reset()
    assert mgr.get_failure_summary()["total_failures"] == 0
