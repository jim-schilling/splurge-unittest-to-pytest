import libcst as cst

from splurge_unittest_to_pytest.stages.steps_remove_unittest_artifacts import (
    ParseRemoveUnittestStep,
    RemoveUnittestArtifactsStep,
)


def _parse(code: str) -> cst.Module:
    return cst.parse_module(code)


def test_remove_unittest_imports_and_testcase_base():
    src = """
import unittest

class MyTest(unittest.TestCase):
    def test_one(self):
        assert True

"""
    mod = _parse(src)
    ctx = {"module": mod}

    p = ParseRemoveUnittestStep()
    r = p.execute(ctx, resources=None)
    assert not r.skipped

    step = RemoveUnittestArtifactsStep()
    res = step.execute({"module": r.delta.values["module"]}, resources=None)
    new_mod = res.delta.values.get("module")
    s = new_mod.code if hasattr(new_mod, "code") else cst.Module([]).code
    assert "import unittest" not in s
    assert "TestCase" not in s


def test_remove_main_block_calls_main():
    src = """
if __name__ == "__main__":
    main()

def main():
    pass
"""
    mod = _parse(src)
    step = RemoveUnittestArtifactsStep()
    res = step.execute({"module": mod}, resources=None)
    new_mod = res.delta.values.get("module")
    s = new_mod.code if hasattr(new_mod, "code") else cst.Module([]).code
    assert "if __name__" not in s
