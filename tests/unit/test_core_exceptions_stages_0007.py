import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_raises_stage_uses_transformer_collected_names_for_non_toplevel_with():
    # assertRaises inside a function; attribute access at module level refers to same name
    src = """
def inner():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()

a = cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new = out.get("module")

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attrs = []

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name):
                    self.attrs.append(node.attr.value)
            except Exception:
                pass

    af = AF()
    new.visit(af)
    assert "value" in af.attrs


def test_simple_statement_line_non_conversion_when_info_none():
    # a bare call to self.notAssertRaises(...) should not convert to With
    src = """
def t():
    self.notAssertRaises(ValueError, func, 1)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    f = Finder()
    out.visit(f)
    assert not f.has_with


def test_is_assert_raises_call_negative_branches():
    src = """
def t():
    with something_else.assertRaises(ValueError):
        pass
    self.other(ValueError)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # Should not have introduced pytest usage
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


def test_raises_stage_integration_exercises_many_branches():
    src = """
def func1(x):
    return x

def func2(x):
    return x

def t():
    with self.assertRaises(ValueError) as cm1:
        raise ValueError()
    a = cm1.exception

    with self.assertRaisesRegex(ValueError, r"pat") as cm2:
        raise ValueError()
    b = cm2.exception

    with self.assertRaisesRegex(ValueError) as cm3:
        raise ValueError()
    c = cm3.exception

    self.assertRaises(ValueError, func1, 1)
    self.assertRaisesRegex(ValueError, r"pat", func2, 2)

    with ctx as cm4:
        pass

    lst = [cm1 for cm1 in range(2)]

    def inner(cm5):
        return cm5.exception

    f = lambda cm6: cm6.exception
    z = cm1.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new = out.get("module")

    class Collector(cst.CSTVisitor):
        def __init__(self) -> None:
            self.pytest_with_count = 0
            self.match_counts = 0
            self.attr_map = {}

        def visit_With(self, node: cst.With) -> None:
            try:
                items = node.items or []
                if not items:
                    return None
                first = items[0]
                call = first.item
                if isinstance(call, cst.Call) and isinstance(call.func, cst.Attribute):
                    func = call.func
                    if (
                        isinstance(func.value, cst.Name)
                        and func.value.value == "pytest"
                        and isinstance(func.attr, cst.Name)
                        and func.attr.value == "raises"
                    ):
                        self.pytest_with_count += 1
                        for a in call.args:
                            if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "match":
                                self.match_counts += 1
                # record asname if present
                if first.asname and isinstance(first.asname.name, cst.Name):
                    self.attr_map[first.asname.name.value] = []
            except Exception:
                pass

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and isinstance(node.attr, cst.Name):
                    name = node.value.value
                    self.attr_map.setdefault(name, []).append(node.attr.value)
            except Exception:
                pass

    coll = Collector()
    new.visit(coll)

    # expect pytest With for cm1, cm2, cm3 and two functional forms converted -> total >= 3
    assert coll.pytest_with_count >= 3
    # cm2 was an assertRaisesRegex with pattern, so at least one match
    assert coll.match_counts >= 1
    # attributes for cm1 should include 'value'
    assert "value" in coll.attr_map.get("cm1", [])
    # inner function param cm5 should preserve 'exception'
    assert "exception" in coll.attr_map.get("cm5", [])
