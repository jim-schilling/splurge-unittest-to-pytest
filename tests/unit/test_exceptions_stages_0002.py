import textwrap
import libcst as cst
from splurge_unittest_to_pytest.stages.raises_stage import RaisesRewriter, ExceptionAttrRewriter


def test_raisesrewriter_made_changes_and_asname_preserved():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x(self):\n                with self.assertRaises(ValueError) as cm:\n                    pass\n        "
    )
    module = cst.parse_module(src)
    transformer = RaisesRewriter()
    new_mod = module.visit(transformer)
    assert transformer.made_changes is True
    found = False

    class V(cst.CSTVisitor):
        def visit_With(self, node: cst.With) -> None:
            nonlocal found
            try:
                items = node.items or []
                if not items:
                    return None
                first = items[0]
                call = first.item
                if (
                    isinstance(call, cst.Call)
                    and isinstance(call.func, cst.Attribute)
                    and isinstance(call.func.value, cst.Name)
                    and (call.func.value.value == "pytest")
                ):
                    asn = first.asname
                    if asn and isinstance(asn.name, cst.Name) and (asn.name.value == "cm"):
                        found = True
            except Exception:
                pass

    new_mod.visit(V())
    assert found


def test_exceptionattrrewriter_respects_lambda_and_function_shadowing():
    src = textwrap.dedent(
        "\n        import pytest\n\n        with pytest.raises(ValueError) as cm:\n            pass\n\n        def outer():\n            x = cm.exception\n\n            def inner(cm):\n                return cm.exception\n\n            return x\n\n        y = cm.exception\n        "
    )
    module = cst.parse_module(src)
    module = module.visit(RaisesRewriter())
    rew = ExceptionAttrRewriter("cm")
    new_mod = module.visit(rew)
    attrs = []

    class C(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm" and isinstance(node.attr, cst.Name):
                    attrs.append(node.attr.value)
            except Exception:
                pass

    new_mod.visit(C())
    assert "value" in attrs
    assert "exception" in attrs
