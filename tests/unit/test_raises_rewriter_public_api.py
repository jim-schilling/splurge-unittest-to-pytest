import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.raises_stage import RaisesRewriter, ExceptionAttrRewriter


def test_raisesrewriter_made_changes_and_asname_preserved():
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                with self.assertRaises(ValueError) as cm:
                    pass
        """
    )
    module = cst.parse_module(src)
    transformer = RaisesRewriter()
    new_mod = module.visit(transformer)

    # transformer should report changes
    assert transformer.made_changes is True

    # verify that a pytest.raises With exists and that 'as cm' is preserved
    found = False

    class V(cst.CSTVisitor):
        def visit_With(self, node: cst.With) -> None:  # type: ignore[override]
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
                    and call.func.value.value == "pytest"
                ):
                    asn = first.asname
                    if asn and isinstance(asn.name, cst.Name) and asn.name.value == "cm":
                        found = True
            except Exception:
                pass

    new_mod.visit(V())
    assert found


def test_exceptionattrrewriter_respects_lambda_and_function_shadowing():
    src = textwrap.dedent(
        """
        import pytest

        with pytest.raises(ValueError) as cm:
            pass

        def outer():
            x = cm.exception

            def inner(cm):
                return cm.exception

            return x

        y = cm.exception
        """
    )
    module = cst.parse_module(src)
    # run the RaisesRewriter first to ensure any normalization it's expected to do
    module = module.visit(RaisesRewriter())
    # now apply ExceptionAttrRewriter publicly
    rew = ExceptionAttrRewriter("cm")
    new_mod = module.visit(rew)

    # collect the attribute names used for 'cm'
    attrs = []

    class C(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:  # type: ignore[override]
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm" and isinstance(node.attr, cst.Name):
                    attrs.append(node.attr.value)
            except Exception:
                pass

    new_mod.visit(C())
    # Expect at least one 'value' for the top-level uses and at least one 'exception' from the inner function param shadowing
    assert "value" in attrs
    assert "exception" in attrs
