import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def test_exceptioninfo_normalizer_applies_value_rewrite_on_preexisting_pytest_with():
    src = textwrap.dedent(
        """
        import pytest

        def test_x():
            with pytest.raises(ValueError) as cm:
                pass
            x = cm.exception
        """
    )
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    assert "module" in out
    new_mod = out["module"]

    # ensure attribute was rewritten to 'value'
    found = False

    class V(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:  # type: ignore[override]
            nonlocal found
            try:
                if (
                    isinstance(node.value, cst.Name)
                    and node.value.value == "cm"
                    and isinstance(node.attr, cst.Name)
                    and node.attr.value == "value"
                ):
                    found = True
            except Exception:
                pass

    new_mod.visit(V())
    assert found


def test_exceptionattrrewriter_respects_function_param_shadowing():
    # If a function defines a parameter named 'cm', the rewriter should not
    # change cm.exception inside that function's scope.
    src = textwrap.dedent(
        """
        import pytest

        with pytest.raises(ValueError) as cm:
            pass

        def f(cm):
            # this 'cm' shadows the top-level 'cm'
            return cm.exception

        # top-level usage should be rewritten
        y = cm.exception
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out["module"]

    func_attr = None
    top_attr = None

    class V(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:  # type: ignore[override]
            nonlocal func_attr, top_attr
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm" and isinstance(node.attr, cst.Name):
                    if node.deep_equals(node):
                        pass
                    # Heuristic: attribute appearing inside FunctionDef will be function scoped
                    _ = getattr(node, "parent", None)
                # We can't rely on parent pointer here; instead collect by textual presence
            except Exception:
                pass

    # Simpler: gather all cm attributes and check there exists one 'value' and one 'exception'
    attrs = []

    class C(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:  # type: ignore[override]
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm" and isinstance(node.attr, cst.Name):
                    attrs.append(node.attr.value)
            except Exception:
                pass

    new_mod.visit(C())
    # we expect top-level rewrite to 'value' and a function-local attribute possibly unchanged 'exception'
    assert "value" in attrs
    assert "exception" in attrs
