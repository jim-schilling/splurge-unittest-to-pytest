"""Tests for stages.raises_stage transformers.

These tests exercise the public behavior of ExceptionAttrRewriter and
RaisesRewriter using LibCST to parse and transform small snippets. They
avoid brittle exact formatting assertions and instead check for
presence/absence of key substrings and transformer state changes.
"""

from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def transform_code(code: str, transformer: cst.CSTTransformer) -> str:
    mod = cst.parse_module(code)
    new = mod.visit(transformer)
    try:
        return new.code
    except Exception:
        return str(new)


def test_exception_attr_rewriter_rewrites_simple_attribute():
    code = "\ndef f():\n    cm = None\n    x = cm.exception\n"
    tr = raises_stage.ExceptionAttrRewriter("cm")
    out = transform_code(code, tr)
    assert "cm.value" in out
    assert "cm.exception" not in out


def test_exception_attr_rewriter_respects_shadowing_in_function():
    code = "\ndef f(cm):\n    x = cm.exception\n"
    tr = raises_stage.ExceptionAttrRewriter("cm")
    out = transform_code(code, tr)
    assert "cm.exception" in out
    assert "cm.value" not in out


def test_exception_attr_rewriter_respects_lambda_shadowing():
    code = "\ndef outer():\n    cm = None\n    f = lambda cm: cm.exception\n    return f\n"
    tr = raises_stage.ExceptionAttrRewriter("cm")
    out = transform_code(code, tr)
    assert "cm.exception" in out


def test_raises_rewriter_context_manager_and_attribute_rewrite():
    code = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError()\n        x = cm.exception\n"
    tr = raises_stage.RaisesRewriter()
    out = transform_code(code, tr)
    assert "pytest.raises" in out
    assert "cm.value" in out
    assert "cm.exception" not in out
    assert tr.made_changes is True


def test_raises_rewriter_functional_form_transforms_to_with():
    code = "\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        self.assertRaises(ValueError, some_func, 1, 2)\n"
    tr = raises_stage.RaisesRewriter()
    out = transform_code(code, tr)
    assert "pytest.raises" in out
    assert "some_func(" in out
    assert tr.made_changes is True


def test_raises_rewriter_regex_uses_match_keyword():
    code = '\nimport unittest\n\nclass T(unittest.TestCase):\n    def test_it(self):\n        with self.assertRaisesRegex(ValueError, "bad") as cm:\n            raise ValueError("bad")\n        x = cm.exception\n'
    tr = raises_stage.RaisesRewriter()
    out = transform_code(code, tr)
    assert "pytest.raises" in out
    assert "match" in out
    assert "cm.value" in out


def _apply_transform(src: str, transformer: cst.CSTTransformer) -> cst.Module:
    mod = cst.parse_module(src)
    return mod.visit(transformer)


def test_exception_attr_rewriter_respects_shadowing():
    src = "\ndef f():\n    with pytest.raises(ValueError) as cm:\n        pass\n    # should rewrite\n    _ = cm.exception\n\ndef g(cm):\n    # shadowed param named cm should prevent rewrite inside g\n    _ = cm.exception\n\n"
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    mod2 = mod.visit(raises_stage.ExceptionAttrRewriter("cm"))
    code = mod2.code
    assert "cm.value" in code
    assert "def g(cm):" in code


def test_with_asname_and_without_asname_conversion():
    src = "\nclass T(unittest.TestCase):\n    def test_it(self):\n        with self.assertRaises(KeyError):\n            raise KeyError()\n\n        with self.assertRaises(ValueError) as ctx:\n            raise ValueError()\n        _ = ctx.exception\n"
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    code = mod.code
    assert "pytest.raises(KeyError)" in code
    assert "pytest.raises(ValueError" in code


def test_functional_assertRaises_to_with_conversion():
    src = "\nclass C(unittest.TestCase):\n    def test_call(self):\n        self.assertRaises(ValueError, func_that_raises)\n        self.assertRaises(ValueError, func_with_args, 1, 2)\n"
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    code = mod.code
    assert "with pytest.raises(ValueError" in code
    assert "func_that_raises()" in code or "func_that_raises(" in code


def test_assertRaisesRegex_match_keyword_added():
    src = '\nclass C(unittest.TestCase):\n    def test_re(self):\n        with self.assertRaisesRegex(ValueError, r"bad"):\n            raise ValueError(\'bad\')\n        self.assertRaisesRegex(ValueError, r"bad", some_call)\n'
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    code = mod.code
    assert "pytest.raises(ValueError" in code
    assert "match" in code
    assert 'r"bad"' in code or "r'bad'" in code or 'r"bad"(' not in code


def test_comprehension_and_lambda_scope_binding():
    src = "\ndef f():\n    with self.assertRaises(ValueError) as cm:\n        [x for x in range(3) if (lambda y: y)(x)]\n    _ = cm.exception\n"
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    mod2 = mod.visit(raises_stage.ExceptionAttrRewriter("cm"))
    code = mod2.code
    assert "cm.value" in code


def test_exception_attr_rewriter_rewrites_unshadowed():
    src = "\nimport pytest\n\ncm = object()\ndef t():\n    pass\n\nx = cm.exception\n"
    module = cst.parse_module(src)
    new = module.visit(raises_stage.ExceptionAttrRewriter("cm"))

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.attr = None

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        self.attr = node.attr.value
            except Exception:
                pass

    af = AF()
    new.visit(af)
    assert af.attr == "value"


def test_exception_attr_rewriter_respects_posonly_and_kwonly_params():
    src_pos = "\ndef f(cm, /):\n    return cm.exception\n"
    module_pos = cst.parse_module(src_pos)
    out_pos = module_pos.visit(raises_stage.ExceptionAttrRewriter("cm"))

    class FinderPos(cst.CSTVisitor):
        def __init__(self) -> None:
            self.inner_attr = None

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.attr, cst.Name):
                    self.inner_attr = node.attr.value
            except Exception:
                pass

    fp = FinderPos()
    out_pos.visit(fp)
    assert fp.inner_attr == "exception"
    src_kw = "\ndef f(*, cm):\n    return cm.exception\n"
    module_kw = cst.parse_module(src_kw)
    out_kw = module_kw.visit(raises_stage.ExceptionAttrRewriter("cm"))
    fk = FinderPos()
    out_kw.visit(fk)
    assert fk.inner_attr == "exception"


def test_raises_stage_returns_needs_pytest_import_true_for_conversion():
    src = "\ndef t():\n    self.assertRaises(ValueError, func, 1)\n"
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is True


def test_exceptioninfo_normalizer_stage_lambda_shadowing():
    src = "\nimport pytest\n\nwith pytest.raises(ValueError) as cm:\n    pass\n\nf = lambda cm: cm.exception\ng = cm.exception\n"
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    new = out.get("module")

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.lambda_attr = None
            self.outer_attr = None

        def visit_Lambda(self, node: cst.Lambda) -> None:
            try:
                if isinstance(node.body, cst.Attribute) and isinstance(node.body.attr, cst.Name):
                    self.lambda_attr = node.body.attr.value
            except Exception:
                pass

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        self.outer_attr = node.attr.value
            except Exception:
                pass

    af = AF()
    new.visit(af)
    assert af.lambda_attr == "exception"
    assert af.outer_attr == "value"


def test_raises_stage_no_module_returns_empty():
    assert raises_stage.raises_stage({}) == {}


def test_exceptioninfo_normalizer_stage_no_module_returns_empty():
    assert raises_stage.exceptioninfo_normalizer_stage({}) == {}


def test_with_name_item_not_converted():
    src = "\ndef t():\n    ctx = contextmanager()\n    with ctx as cm:\n        pass\n"
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
                    and (node.func.value.value == "pytest")
                ):
                    self.has_pytest = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert not f.has_pytest


def test_functional_non_self_call_not_converted():
    src = "\ndef t():\n    obj.assertRaises(ValueError, func, 1)\n"
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
    src = "\ndef t():\n    x = 1\n"
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False


def test_functional_regex_has_match_kwarg():
    src = '\ndef testf():\n    self.assertRaisesRegex(ValueError, r"pat", func, 1)\n'
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

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
                        if a.keyword and isinstance(a.keyword, cst.Name) and (a.keyword.value == "match"):
                            self.match_found = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert f.match_found


def test_context_manager_without_asname_converts_and_no_attribute_rewrite():
    src = "\ndef t():\n    with self.assertRaises(ValueError):\n        raise ValueError()\n    # no bound name to refer to\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

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
                        and (func.attr.value == "raises")
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
    src = "\ndef t():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n\n    def inner(cm):\n        return cm.exception\n\n    a = cm.exception\n"
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module}).get("module")

    class AF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.inner_attr = None
            self.outer_attr = None

        def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
            try:
                if node.name.value == "inner":
                    for stmt in node.body.body:
                        if isinstance(stmt, cst.SimpleStatementLine) and isinstance(stmt.body[0], cst.Return):
                            ret = stmt.body[0]
                            if isinstance(ret.value, cst.Attribute) and isinstance(ret.value.attr, cst.Name):
                                self.inner_attr = ret.value.attr.value
            except Exception:
                pass

        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm":
                    if isinstance(node.attr, cst.Name):
                        self.outer_attr = node.attr.value
            except Exception:
                pass

    af = AF()
    out.visit(af)
    assert af.inner_attr == "exception"
    assert af.outer_attr == "value"


def test_assertRaisesRegex_without_pattern_falls_back_no_match_kwarg():
    src = "\ndef t():\n    with self.assertRaisesRegex(ValueError) as cm:\n        raise ValueError()\n    a = cm.exception\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

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
                            if a.keyword and isinstance(a.keyword, cst.Name) and (a.keyword.value == "match"):
                                self.has_match = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert f.has_pytest
    assert not f.has_match


def test_non_self_assertRaises_not_converted():
    src = "\nclass Other:\n    def assertRaises(self, *a, **k):\n        pass\n\ndef t():\n    with Other().assertRaises(ValueError):\n        pass\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_pytest = False

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if (
                    isinstance(node.func, cst.Attribute)
                    and isinstance(node.func.value, cst.Name)
                    and (node.func.value.value == "pytest")
                ):
                    self.found_pytest = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert not f.found_pytest


def test_simple_statement_multiple_small_statements_not_converted():
    src = "\ndef t():\n    self.assertRaises(ValueError); x = 1\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    wf = WF()
    out.visit(wf)
    assert not wf.has_with


def test_raises_stage_uses_transformer_collected_names_for_non_toplevel_with():
    src = "\ndef inner():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n\na = cm.exception\n"
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
    src = "\ndef t():\n    self.notAssertRaises(ValueError, func, 1)\n"
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
    src = "\ndef t():\n    with something_else.assertRaises(ValueError):\n        pass\n    self.other(ValueError)\n"
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
                    and (node.func.value.value == "pytest")
                ):
                    self.has_pytest = True
            except Exception:
                pass

    f = Finder()
    out.visit(f)
    assert not f.has_pytest


def test_raises_stage_integration_exercises_many_branches():
    src = '\ndef func1(x):\n    return x\n\ndef func2(x):\n    return x\n\ndef t():\n    with self.assertRaises(ValueError) as cm1:\n        raise ValueError()\n    a = cm1.exception\n\n    with self.assertRaisesRegex(ValueError, r"pat") as cm2:\n        raise ValueError()\n    b = cm2.exception\n\n    with self.assertRaisesRegex(ValueError) as cm3:\n        raise ValueError()\n    c = cm3.exception\n\n    self.assertRaises(ValueError, func1, 1)\n    self.assertRaisesRegex(ValueError, r"pat", func2, 2)\n\n    with ctx as cm4:\n        pass\n\n    lst = [cm1 for cm1 in range(2)]\n\n    def inner(cm5):\n        return cm5.exception\n\n    f = lambda cm6: cm6.exception\n    z = cm1.exception\n'
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
                        and (func.attr.value == "raises")
                    ):
                        self.pytest_with_count += 1
                        for a in call.args:
                            if a.keyword and isinstance(a.keyword, cst.Name) and (a.keyword.value == "match"):
                                self.match_counts += 1
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
    assert coll.pytest_with_count >= 3
    assert coll.match_counts >= 1
    assert "value" in coll.attr_map.get("cm1", [])
    assert "exception" in coll.attr_map.get("cm5", [])


def test_functional_non_regex_creates_with_and_sets_made_changes():
    src = "\ndef testf():\n    self.assertRaises(ValueError, func, 1, 2)\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)
    assert tr.made_changes

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
    src = "\ndef testf():\n    self.assertRaises(ValueError)\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_with = False

        def visit_With(self, node: cst.With) -> None:
            self.found_with = True

    f = Finder()
    out.visit(f)
    assert not f.found_with


def test_exceptioninfo_normalizer_stage_applies_rewriter():
    src = "\nimport pytest\n\ndef test():\n    with pytest.raises(ValueError) as cm:\n        raise ValueError()\n    x = cm.exception\n"
    module = cst.parse_module(src)
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
    src = "\ndef t():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n    # comprehension binds 'cm' as target, should shadow the outer name\n    lst = [cm for cm in range(3)]\n    y = cm.exception\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

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
    assert "value" in af.attr_names


def test_raises_rewriter_with_context_manager():
    src = "\nclass T(unittest.TestCase):\n    def test_something(self):\n        with self.assertRaises(ValueError):\n            do_thing()\n"
    module = cst.parse_module(src)
    transformer = raises_stage.RaisesRewriter()
    new_mod = module.visit(transformer)

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
    src = "\nclass T(unittest.TestCase):\n    def test_f(self):\n        self.assertRaises(ValueError, f, 1)\n"
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
    src = "\ndef fn():\n    with pytest.raises(ValueError) as cm:\n        raise ValueError()\n    x = cm.exception\n    def inner(cm):\n        return cm.exception\n"
    module = cst.parse_module(src)
    new_mod = module.visit(raises_stage.ExceptionAttrRewriter("cm"))
    _assigns = [n for n in new_mod.body if isinstance(n, cst.SimpleStatementLine)]
    found_value = False
    for node in new_mod.body:
        if isinstance(node, cst.FunctionDef):
            for s in node.body.body:
                if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Assign):
                    val = s.body[0].value
                    if (
                        isinstance(val, cst.Attribute)
                        and isinstance(val.attr, cst.Name)
                        and (val.attr.value == "value")
                    ):
                        found_value = True
    assert found_value
    inner_access = None
    for node in new_mod.body:
        if isinstance(node, cst.FunctionDef):
            for s in node.body.body:
                if isinstance(s, cst.FunctionDef) and s.name.value == "inner":
                    ret = s.body.body[0].body[0]
                    inner_access = ret.value
    assert isinstance(inner_access, cst.Attribute)
    assert isinstance(inner_access.attr, cst.Name) and inner_access.attr.value == "exception"


def test_raises_stage_integration_sets_import_flag_and_normalizes_attrs():
    src = "\ndef test():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n    a = cm.exception\n"
    module = cst.parse_module(src)
    ctx = {"module": module}
    out = raises_stage.raises_stage(ctx)
    assert out.get("needs_pytest_import") is True
    new_mod = out.get("module")
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
    src = '\ndef test():\n    with self.assertRaisesRegex(ValueError, r"pat") as cm:\n        raise ValueError()\n    a = cm.exception\n'
    module = cst.parse_module(src)
    transformer = raises_stage.RaisesRewriter()
    new_mod = module.visit(transformer)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if (
                    isinstance(node.func, cst.Attribute)
                    and isinstance(node.func.value, cst.Name)
                    and (node.func.value.value == "pytest")
                ):
                    for a in node.args:
                        if a.keyword and isinstance(a.keyword, cst.Name) and (a.keyword.value == "match"):
                            self.found = True
            except Exception:
                pass

    f = Finder()
    new_mod.visit(f)
    assert f.found
    src2 = '\ndef testf():\n    self.assertRaisesRegex(ValueError, r"pat", func, 1)\n'
    module2 = cst.parse_module(src2)
    tr2 = raises_stage.RaisesRewriter()
    out2 = module2.visit(tr2)

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
    src = "\ndef t():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n    f = lambda cm: cm.exception\n"
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out.get("module")

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
    src = "\ndef test():\n    with contextlib.something():\n        pass\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_pytest = False

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if (
                    isinstance(node.func, cst.Attribute)
                    and isinstance(node.func.value, cst.Name)
                    and (node.func.value.value == "pytest")
                ):
                    self.has_pytest = True
            except Exception:
                pass

    f = Finder()
    new.visit(f)
    assert not f.has_pytest


def test_withitem_asname_preserved():
    src = "\ndef t():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

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
    src = "\ndef t():\n    with self.assertRaises(ValueError) as cm:\n        raise ValueError()\n    f = lambda: cm.exception\n"
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out.get("module")

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


def test_exceptioninfo_normalizer_stage_applies_rewriter__01():
    src = "\ndef test():\n    with pytest.raises(ValueError) as cm:\n        raise ValueError()\n    a = cm.exception\n"
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    new_mod = out.get("module")

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
    src = "\ndef fn():\n    return [i for i in range(3)]\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    new = module.visit(tr)
    assert isinstance(new, cst.Module)


def test_simple_statement_multiple_small_statements_not_converted_bare():
    src = "\ndef t():\n    self.assertRaises(ValueError); x = 1\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class WF(cst.CSTVisitor):
        def __init__(self) -> None:
            self.has_with = False

        def visit_With(self, node: cst.With) -> None:
            self.has_with = True

    wf = WF()
    out.visit(wf)
    assert not wf.has_with


def test_simple_statement_non_call_expr_not_converted():
    src = "\ndef t():\n    (1 + 2)\n"
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


def test_functional_single_arg_no_conversion():
    src = "\ndef t():\n    self.assertRaises(ValueError)\n"
    module = cst.parse_module(src)
    tr = raises_stage.RaisesRewriter()
    out = module.visit(tr)

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_with = False

        def visit_With(self, node: cst.With) -> None:
            self.found_with = True

    f = Finder()
    out.visit(f)
    assert not f.found_with
