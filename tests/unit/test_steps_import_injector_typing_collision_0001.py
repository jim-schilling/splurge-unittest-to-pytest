import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import InsertImportsStep


def test_respects_user_defined_names_named_like_typing():
    src = textwrap.dedent("""
    class Dict:
        pass

    def f(x: Dict):
        pass
    """)

    mod = cst.parse_module(src)
    ctx = {"module": mod}
    res = InsertImportsStep().execute(ctx, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    # Should not insert `from typing import Dict` because Dict is user-defined
    assert "from typing import Dict" not in new_mod.code
