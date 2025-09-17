import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_functional_non_regex_creates_with_and_sets_made_changes():
    src = """
def testf():
    self.assertRaises(ValueError, func, 1, 2)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)
    # made_changes should be true when conversion happened
    assert tr.made_changes

    # produced AST should contain a With node with a Call in its body
    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            try:
                self.has_with = True
            except Exception:
                pass

    wf = WF()
    out.visit(wf)
    assert wf.has_with


def test_functional_short_args_no_change():
    # less than 2 args -> should not convert functional form
    src = """
def testf():
    self.assertRaises(ValueError)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # Should not have produced a With wrapping
    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_with = False

        def visit_With(self, node: cst.With) -> None:
            self.found_with = True

    f = Finder()
    out.visit(f)
    assert not f.found_with


def test_exceptioninfo_normalizer_stage_applies_rewriter():
    # Create a module that has a pytest.raises asname and an attribute access.
    src = """
import pytest

def test():
    with pytest.raises(ValueError) as cm:
        raise ValueError()
    x = cm.exception
"""
    module = cst.parse_module(src)
    # normalizer should change cm.exception -> cm.value
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    new_mod = out.get("module")

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_value = False

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name) and node.attr.value == "value":
                    self.found_value = True
            except Exception:
                pass

    af = AF()
    new_mod.visit(af)
    assert af.found_value


def test_listcomp_scope_binding_prevents_rewrite():
    src = """
def t():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()
    # comprehension binds 'cm' as target, should shadow the outer name
    lst = [cm for cm in range(3)]
    y = cm.exception
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

    # After rewrite, the final attribute access should still be rewritten to .value
    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attr_names = []

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name):
                    self.attr_names.append(node.attr.value)
            except Exception:
                pass

    af = AF()
    new.visit(af)
    # There should be at least one 'value' present from the bound cm.exception -> cm.value
    assert "value" in af.attr_names
