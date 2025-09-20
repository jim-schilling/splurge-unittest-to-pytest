import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_tidy import (
    NormalizeSpacingStep,
    EnsureSelfParamStep,
)


def test_tidy_pipeline_runs_and_modifies_module():
    src = textwrap.dedent("""
    class TestThing:
        def test_method():
            assert True

    def helper():
        pass
    """)

    context = {"module": cst.parse_module(src), "__stage_id__": "stages.tidy"}
    resources = {}

    steps = [NormalizeSpacingStep(), EnsureSelfParamStep()]
    result = run_steps("stages.tidy", "tasks.tidy.pipeline", "tidy_pipeline", steps, context, resources)

    assert result
    assert result.delta
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    out_src = new_mod.code
    assert "def test_method(self)" in out_src
    # ensure spacing normalization didn't remove class or helper
    assert "class TestThing" in out_src
    assert "def helper" in out_src
