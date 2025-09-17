import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def test_raises_rewriter_with_context_manager():
    src = """
class T(unittest.TestCase):
    def test_something(self):
        with self.assertRaises(ValueError):
            do_thing()
"""
    module = cst.parse_module(src)
    transformer = raises_stage.RaisesRewriter()
    new_mod = module.visit(transformer)

    # should have introduced pytest.raises somewhere in the transformed tree
    class _Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_With(self, node: cst.With) -> None:
            try:
                first = node.items[0]
                call = first.item
                if isinstance(call, cst.Call) and isinstance(call.func, cst.Attribute):
                    if isinstance(call.func.value, cst.Name) and call.func.value.value == "pytest":
                        self.found = True
            except Exception:
                pass

    finder = _Finder()
    new_mod.visit(finder)
    assert finder.found
    assert transformer.made_changes


def test_raises_rewriter_functional_form():
    src = """
class T(unittest.TestCase):
    def test_f(self):
        self.assertRaises(ValueError, f, 1)
"""
    module = cst.parse_module(src)
    transformer = raises_stage.RaisesRewriter()
    new_mod = module.visit(transformer)

    class _WithFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    wf = _WithFinder()
    new_mod.visit(wf)
    assert wf.has_with


def test_exception_attr_rewriter_and_shadowing():
    # when name is bound by pytest.raises as cm, attribute access cm.exception -> cm.value
    src = """
def fn():
    with pytest.raises(ValueError) as cm:
        raise ValueError()
    x = cm.exception
    def inner(cm):
        return cm.exception
"""
    module = cst.parse_module(src)
    # apply ExceptionAttrRewriter for name 'cm'
    new_mod = module.visit(raises_stage.ExceptionAttrRewriter("cm"))
    # top-level assignment should use .value
    # top-level assignment nodes (not used directly; present for clarity)
    _assigns = [n for n in new_mod.body if isinstance(n, cst.SimpleStatementLine)]
    # find the assignment to x
    found_value = False
    for node in new_mod.body:
        if isinstance(node, cst.FunctionDef):
            for s in node.body.body:
                if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Assign):
                    # assignment target x = cm.value
                    val = s.body[0].value
                    if isinstance(val, cst.Attribute) and isinstance(val.attr, cst.Name) and val.attr.value == "value":
                        found_value = True
    assert found_value
    # inner function has a parameter named cm, its attribute access should remain .exception
    inner_access = None
    for node in new_mod.body:
        if isinstance(node, cst.FunctionDef):
            for s in node.body.body:
                if isinstance(s, cst.FunctionDef) and s.name.value == "inner":
                    # inner body first statement return cm.exception
                    ret = s.body.body[0].body[0]
                    inner_access = ret.value
    assert isinstance(inner_access, cst.Attribute)
    assert isinstance(inner_access.attr, cst.Name) and inner_access.attr.value == "exception"


def test_raises_stage_integration_sets_import_flag_and_normalizes_attrs():
    src = """
def test():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()
    a = cm.exception
"""
    module = cst.parse_module(src)
    ctx = {"module": module}
    out = raises_stage.raises_stage(ctx)
    assert out.get("needs_pytest_import") is True
    new_mod = out.get("module")
    # verify a = cm.value now
    found = False
    for node in new_mod.body:
        if isinstance(node, cst.FunctionDef):
            for s in node.body.body:
                if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Assign):
                    val = s.body[0].value
                    if isinstance(val, cst.Attribute) and val.attr.value == "value":
                        found = True
    assert found


def test_assertRaisesRegex_context_and_functional_variants():
    # context manager regex variant
    src = """
def test():
    with self.assertRaisesRegex(ValueError, r"pat") as cm:
        raise ValueError()
    a = cm.exception
"""
    module = cst.parse_module(src)
    transformer = raises_stage.RaisesRewriter()
    new_mod = module.visit(transformer)
    # find pytest.raises call and ensure it has a match= keyword argument when Regex
    # detector below sets Finder.found

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if (
                    isinstance(node.func, cst.Attribute)
                    and isinstance(node.func.value, cst.Name)
                    and node.func.value.value == "pytest"
                ):
                    # check for keyword 'match' in args
                    for a in node.args:
                        if a.keyword and isinstance(a.keyword, cst.Name) and a.keyword.value == "match":
                            self.found = True
            except Exception:
                pass

    f = Finder()
    new_mod.visit(f)
    assert f.found

    # functional form with Regex: should produce a With wrapping the call and match kwarg on pytest.raises
    src2 = """
def testf():
    self.assertRaisesRegex(ValueError, r"pat", func, 1)
"""
    module2 = cst.parse_module(src2)
    tr2 = raises_stage.RaisesRewriter()
    out2 = module2.visit(tr2)

    # ensure With present and inner contains a Call expression (functional form converted)
    class WithFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_call = False

        def visit_With(self, node: cst.With) -> None:
            try:
                body = node.body
                for stmt in body.body:
                    if isinstance(stmt, cst.SimpleStatementLine) and isinstance(stmt.body[0], cst.Expr):
                        call = stmt.body[0].value
                        if isinstance(call, cst.Call):
                            self.found_call = True
            except Exception:
                pass

    wf = WithFinder()
    out2.visit(wf)
    assert wf.found_call


def test_lambda_param_shadowing_no_rewrite():
    src = """
def t():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()
    f = lambda cm: cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out.get("module")

    # lambda parameter 'cm' should shadow outer name; inside lambda attribute should remain 'exception'
    class LF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attr = None

        def visit_Lambda(self, node: cst.Lambda) -> None:
            try:
                if isinstance(node.body, cst.Attribute):
                    self.attr = node.body.attr.value
            except Exception:
                pass

    lf = LF()
    new_mod.visit(lf)
    assert lf.attr == "exception"


def test_non_assertRaises_with_unchanged():
    src = """
def test():
    with contextlib.something():
        pass
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

    # no pytest.raises introduced
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


def test_withitem_asname_preserved():
    src = """
def t():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    # find With and check its first item's asname exists
    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.asname = None

        def visit_With(self, node: cst.With) -> None:
            try:
                first = node.items[0]
                if first.asname and isinstance(first.asname.name, cst.Name):
                    self.asname = first.asname.name.value
            except Exception:
                pass

    wf = WF()
    out.visit(wf)
    assert wf.asname == "cm"


def test_lambda_attribute_rewritten_by_stage():
    src = """
def t():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()
    f = lambda: cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out.get("module")

    # find lambda and verify it now references .value
    class LambdaFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attr_name = None

        def visit_Lambda(self, node: cst.Lambda) -> None:
            try:
                body = node.body
                if isinstance(body, cst.Attribute):
                    self.attr_name = body.attr.value
            except Exception:
                pass

    lf = LambdaFinder()
    new_mod.visit(lf)
    assert lf.attr_name == "value"


def test_exceptioninfo_normalizer_stage_applies_rewriter():
    src = """
def test():
    with pytest.raises(ValueError) as cm:
        raise ValueError()
    a = cm.exception
"""
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    new_mod = out.get("module")
    # ensure attribute rewritten
    # AFinder sets its internal flag

    class AFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.ok = False

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name) and node.attr.value == "value":
                    self.ok = True
            except Exception:
                pass

    af = AFinder()
    new_mod.visit(af)
    assert af.ok


def test_visit_listcomp_traversal_exercised():
    src = """
def fn():
    return [i for i in range(3)]
"""
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    # just ensure traversal runs without error and returns a Module
    new = module.visit(tr)
    assert isinstance(new, cst.Module)
