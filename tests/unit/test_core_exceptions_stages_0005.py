import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_functional_regex_has_match_kwarg():
    src = """
def testf():
    self.assertRaisesRegex(ValueError, r"pat", func, 1)
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # find the With node and inspect its first item's Call args for a keyword 'match'
    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.match_found = False

        def visit_With(self, node: cst.With) -> None:
            try:
                items = node.items or []
                if not items:
                    return None
                first = items[0]
                call = first.item
                if isinstance(call, cst.Call):
                    for a in call.args:
                        if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "match":
                            self.match_found = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert f.match_found


def test_context_manager_without_asname_converts_and_no_attribute_rewrite():
    src = """
def t():
    with self.assertRaises(ValueError):
        raise ValueError()
    # no bound name to refer to
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

    # ensure With exists and it's calling pytest.raises (no asname)
    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_pytest_raises = False
            self.any_asname = False

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
                        self.has_pytest_raises = True
                if first.asname is not None:
                    self.any_asname = True
            except Exception:
                pass

    wf = WF()
    new.visit(wf)
    assert wf.has_pytest_raises
    assert not wf.any_asname


def test_function_param_shadowing_prevents_attribute_rewrite():
    src = """
def t():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()

    def inner(cm):
        return cm.exception

    a = cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module}).get("module")

    # attributes: inner function param should keep .exception (shadowing), outer access should be .value
    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.inner_attr = None
            self.outer_attr = None

        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            try:
                if node.name.value == "inner":
                    # find return statement inside
                    for stmt in node.body.body:
                        if isinstance(stmt, cst.SimpleStatementLine) and isinstance(stmt.body[0], cst.Return):
                            ret = stmt.body[0]
                            if isinstance(ret.value, cst.Attribute) and isinstance(ret.value.attr, cst.Name):
                                self.inner_attr = ret.value.attr.value
            except Exception:
                pass

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                # catch outer attribute: cm.exception reference after inner
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        # prefer to set outer if not in inner
                        self.outer_attr = node.attr.value
            except Exception:
                pass

    af = AF()
    out.visit(af)
    assert af.inner_attr == "exception"
    assert af.outer_attr == "value"
