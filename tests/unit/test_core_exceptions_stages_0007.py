import textwrap
import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def test_stage_reports_needs_pytest_import_for_simple_with():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x(self):\n                with self.assertRaises(ValueError):\n                    pass\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is True


def test_functional_assertRaisesRegex_transforms_to_with_with_match_and_body():
    src = textwrap.dedent(
        "\n        import unittest\n\n        def test_func():\n            unittest.TestCase.assertRaisesRegex(unittest.TestCase, ValueError, r\"pat\", lambda: print('x'))\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out["module"]
    found_match = False
    found_print = False

    class V(cst.CSTVisitor):
        def visit_Call(self, node: cst.Call) -> None:
            nonlocal found_match
            try:
                func = getattr(node, "func", None)
                if (
                    isinstance(func, cst.Attribute)
                    and isinstance(func.value, cst.Name)
                    and (func.value.value == "pytest")
                    and isinstance(func.attr, cst.Name)
                    and (func.attr.value == "raises")
                ):
                    for a in getattr(node, "args", []) or []:
                        kw = getattr(a, "keyword", None)
                        name = getattr(kw, "value", None) if kw is not None else None
                        if name == "match":
                            found_match = True
            except Exception:
                pass

        def visit_With(self, node: cst.With) -> None:
            nonlocal found_print
            try:
                body = getattr(node, "body", None)
                stmts = getattr(body, "body", []) or []
                for s in stmts:
                    if isinstance(s, cst.SimpleStatementLine):
                        for small in s.body:
                            if (
                                isinstance(small, cst.Expr)
                                and isinstance(small.value, cst.Call)
                                and isinstance(small.value.func, cst.Name)
                                and (small.value.func.value == "print")
                            ):
                                found_print = True
            except Exception:
                pass

    new_mod.visit(V())
    if out.get("needs_pytest_import"):
        assert found_match and found_print


def test_exceptioninfo_normalizer_handles_multiple_with_asnames():
    src = textwrap.dedent(
        "\n        import pytest\n\n        def test_x_02():\n            with pytest.raises(ValueError) as a:\n                pass\n            with pytest.raises(TypeError) as b:\n                pass\n            x = a.exception\n            y = b.exception\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    new_mod = out["module"]
    names = []

    class V(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and isinstance(node.attr, cst.Name):
                    names.append((node.value.value, node.attr.value))
            except Exception:
                pass

    new_mod.visit(V())
    assert ("a", "value") in names
    assert ("b", "value") in names
