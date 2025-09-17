import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_assertRaisesRegex_without_pattern_falls_back_no_match_kwarg():
    src = """
def t():
    with self.assertRaisesRegex(ValueError) as cm:
        raise ValueError()
    a = cm.exception
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # the pytest.raises call should exist but not have a 'match' keyword
    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_match = False
            self.has_pytest = False

        def visit_With(self, node: cst.With) -> None:
            try:
                items = node.items or []
                if not items:
                    return None
                first = items[0]
                call = first.item
                if isinstance(call, cst.Call) and isinstance(call.func, cst.Attribute):
                    func = call.func
                    if isinstance(func.value, cst.Name) and func.value.value == "pytest":
                        self.has_pytest = True
                        for a in call.args:
                            if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "match":
                                self.has_match = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert f.has_pytest
    assert not f.has_match


def test_non_self_assertRaises_not_converted():
    src = """
class Other:
    def assertRaises(self, *a, **k):
        pass

def t():
    with Other().assertRaises(ValueError):
        pass
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # Should not find pytest.raises usage
    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_pytest = False

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if (
                    isinstance(node.func, cst.Attribute)
                    and isinstance(node.func.value, cst.Name)
                    and node.func.value.value == "pytest"
                ):
                    self.found_pytest = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert not f.found_pytest


def test_simple_statement_multiple_small_statements_not_converted():
    src = """
def t():
    self.assertRaises(ValueError); x = 1
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # no With should be introduced by conversion in this case
    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    wf = WF()
    out.visit(wf)
    assert not wf.has_with
