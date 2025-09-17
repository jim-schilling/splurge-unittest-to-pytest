import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_raises_stage_no_module_returns_empty():
    assert raises_stage.raises_stage({}) == {}


def test_exceptioninfo_normalizer_stage_no_module_returns_empty():
    assert raises_stage.exceptioninfo_normalizer_stage({}) == {}


def test_with_name_item_not_converted():
    # with ctx as x: where ctx is a Name (not a Call) should be left unchanged
    src = """
def t():
    ctx = contextmanager()
    with ctx as cm:
        pass
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_pytest = False

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if (
                    isinstance(node.func, cst.Attribute)
                    and isinstance(node.func.value, cst.Name)
                    and node.func.value.value == "pytest"
                ):
                    self.has_pytest = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert not f.has_pytest


def test_functional_non_self_call_not_converted():
    # obj.assertRaises should not be detected (only self.assertRaises)
    src = """
def t():
    obj.assertRaises(ValueError, func, 1)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_with = False

        def visit_With(self, node: cst.With) -> None:
            self.found_with = True

    wf = WF()
    out.visit(wf)
    assert not wf.found_with


def test_raises_stage_needs_pytest_import_false_when_no_conversion():
    src = """
def t():
    x = 1
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
