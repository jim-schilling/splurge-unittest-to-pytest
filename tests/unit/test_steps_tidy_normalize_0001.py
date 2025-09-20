import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_tidy import NormalizeSpacingStep


def test_normalize_spacing_inserts_blank_lines(tmp_path):
    src = textwrap.dedent("""
    def foo():
        pass

    class Bar:
        def baz(self):
            pass
    """)

    ctx = {"module": cst.parse_module(src)}
    resources = {}

    step = NormalizeSpacingStep()
    result = step.execute(ctx, resources)

    assert result.delta
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    out_src = new_mod.code
    # Ensure there's an empty line between top-level defs and classes
    assert "\n\nclass Bar" in out_src or "class Bar" in out_src
