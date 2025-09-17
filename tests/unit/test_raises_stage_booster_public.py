import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_top_level_withs_are_collected_and_normalized():
    # Top-level with should be found by raises_stage collection loop
    src = """
with self.assertRaises(ValueError) as cm:
    raise ValueError()
x = cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new = out.get("module")
    assert out.get("needs_pytest_import") is True

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_value = False

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name) and node.attr.value == "value":
                    self.found_value = True
            except Exception:
                pass

    f = Finder()
    new.visit(f)
    assert f.found_value


def test_withitem_first_item_not_call_is_ignored():
    # first.item is a Name expression (not a Call) -> ignored by leave_With/top-level collection
    src = """
with ctx as cm:
    pass
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

    # nothing changed to pytest
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
    new.visit(f)
    assert not f.has_pytest


def test_top_level_with_call_but_not_pytest_raises_skipped_for_names():
    # with a Call expression whose func is an attribute but not pytest.raises should be skipped
    src = """
with other.raises(ValueError) as cm:
    raise ValueError()
y = cm.exception
"""
    module = cst.parse_module(src)
    # run the stage to ensure collector iterates and does not crash
    out = raises_stage.raises_stage({"module": module})
    new = out.get("module")

    # ensure the attribute access remains (no pytest conversion)
    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.seen = False

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        self.seen = True
            except Exception:
                pass

    af = AF()
    new.visit(af)
    assert af.seen
