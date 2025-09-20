import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def test_exceptioninfo_normalizer_applies_value_rewrite_on_preexisting_pytest_with():
    src = textwrap.dedent(
        "\n        import pytest\n\n        def test_x():\n            with pytest.raises(ValueError) as cm:\n                pass\n            x = cm.exception\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.exceptioninfo_normalizer_stage({"module": module})
    assert "module" in out
    new_mod = out["module"]
    found = False

    class V(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:
            nonlocal found
            try:
                if (
                    isinstance(node.value, cst.Name)
                    and node.value.value == "cm"
                    and isinstance(node.attr, cst.Name)
                    and (node.attr.value == "value")
                ):
                    found = True
            except Exception:
                pass

    new_mod.visit(V())
    assert found


def test_exceptionattrrewriter_respects_function_param_shadowing():
    src = textwrap.dedent(
        "\n        import pytest\n\n        with pytest.raises(ValueError) as cm:\n            pass\n\n        def f(cm):\n            # this 'cm' shadows the top-level 'cm'\n            return cm.exception\n\n        # top-level usage should be rewritten\n        y = cm.exception\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out["module"]
    func_attr = None
    top_attr = None

    class V(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:
            nonlocal func_attr, top_attr
            try:
                if isinstance(node.value, cst.Name) and node.value.value == "cm" and isinstance(node.attr, cst.Name):
                    if node.deep_equals(node):
                        pass
                    _ = getattr(node, "parent", None)
            except Exception:
                pass

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
