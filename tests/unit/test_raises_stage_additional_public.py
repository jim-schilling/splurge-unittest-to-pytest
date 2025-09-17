import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def _find_attributes_for_name(module: cst.Module, name: str) -> list[cst.Attribute]:
    found: list[cst.Attribute] = []

    class _Visitor(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:  # type: ignore[override]
            try:
                if isinstance(node.value, cst.Name) and node.value.value == name:
                    found.append(node)
            except Exception:
                pass

    module.visit(_Visitor())
    return found


def test_with_asname_and_attribute_rewritten_to_value():
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                with self.assertRaises(ValueError) as cm:
                    pass
                # reference after the with
                _ = cm.exception
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is True
    new_mod = out["module"]

    attrs = _find_attributes_for_name(new_mod, "cm")
    # there should be at least one Attribute and it should have attr 'value'
    assert any(isinstance(a.attr, cst.Name) and a.attr.value == "value" for a in attrs)


def test_shadowing_in_lambda_prevents_rewrite_but_outside_is_rewritten():
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                with self.assertRaises(ValueError) as cm:
                    pass
                f = lambda cm: cm.exception
                g = lambda: cm.exception
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out["module"]

    attrs = _find_attributes_for_name(new_mod, "cm")
    # We expect at least one 'value' (the g lambda closure or outside use) and at least one 'exception' from the lambda parameter
    has_value = any(isinstance(a.attr, cst.Name) and a.attr.value == "value" for a in attrs)
    has_exception = any(isinstance(a.attr, cst.Name) and a.attr.value == "exception" for a in attrs)
    assert has_value and has_exception


def test_assertRaisesRegex_without_pattern_uses_fallback_no_match_kw():
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                with self.assertRaisesRegex(ValueError):
                    raise ValueError('x')
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out["module"]

    # find top-level With calls to pytest.raises and inspect their Call.args for absence of match kw
    class _Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_Call(self, node: cst.Call) -> None:  # type: ignore[override]
            try:
                func = getattr(node, "func", None)
                if (
                    isinstance(func, cst.Attribute)
                    and isinstance(func.value, cst.Name)
                    and func.value.value == "pytest"
                    and isinstance(func.attr, cst.Name)
                    and func.attr.value == "raises"
                ):
                    args = getattr(node, "args", []) or []
                    for a in args:
                        kw = getattr(a, "keyword", None)
                        name = getattr(kw, "value", None) if kw is not None else None
                        assert name != "match"
                    self.found = True
            except Exception:
                pass

    finder = _Finder()
    new_mod.visit(finder)
    assert finder.found


def test_functional_assertRaises_transforms_to_with_body_call():
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                self.assertRaises(ValueError, print, 'hello')
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is True
    new_mod = out["module"]

    # find created With and ensure body contains a Call to 'print'
    class _WithBodyFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found = False

        def visit_With(self, node: cst.With) -> None:  # type: ignore[override]
            try:
                body = getattr(node, "body", None)
                stmts = getattr(body, "body", []) or []
                for s in stmts:
                    if isinstance(s, cst.SimpleStatementLine):
                        for small in s.body:
                            if isinstance(small, cst.Expr) and isinstance(small.value, cst.Call):
                                if isinstance(small.value.func, cst.Name) and small.value.func.value == "print":
                                    self.found = True
            except Exception:
                pass

    finder = _WithBodyFinder()
    new_mod.visit(finder)
    assert finder.found
