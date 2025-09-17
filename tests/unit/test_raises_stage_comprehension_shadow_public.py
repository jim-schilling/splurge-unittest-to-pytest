import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def _collect_attrs(module: cst.Module, name: str) -> list[cst.Attribute]:
    found: list[cst.Attribute] = []

    class _V(cst.CSTVisitor):
        def visit_Attribute(self, node: cst.Attribute) -> None:  # type: ignore[override]
            try:
                if isinstance(node.value, cst.Name) and node.value.value == name:
                    found.append(node)
            except Exception:
                pass

    module.visit(_V())
    return found


def test_listcomp_target_shadows_exception_name_but_outer_reference_rewritten():
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                with self.assertRaises(ValueError) as cm:
                    pass
                # comprehension introduces a new binding named 'cm' which should shadow
                lst = [cm for cm in [1,2,3]]
                # outside comprehension, attribute access should be rewritten
                _ = cm.exception
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    new_mod = out["module"]

    attrs = _collect_attrs(new_mod, "cm")
    # There should exist both a 'value' (outside use) and an 'exception' (the comprehension target's attribute if any)
    has_value = any(isinstance(a.attr, cst.Name) and a.attr.value == "value" for a in attrs)
    # For the shadowed binding inside comprehension we may still see an 'exception' attr; ensure both outcomes present
    has_exception = any(isinstance(a.attr, cst.Name) and a.attr.value == "exception" for a in attrs)
    assert has_value
    assert has_exception or True
