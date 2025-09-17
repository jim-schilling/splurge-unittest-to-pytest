import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def _has_with_nodes(module: cst.Module) -> bool:
    found = False

    class _V(cst.CSTVisitor):
        def visit_With(self, node: cst.With) -> None:  # type: ignore[override]
            nonlocal found
            found = True

    module.visit(_V())
    return found


def test_multi_statement_simple_statement_line_is_not_transformed():
    # multiple small-statements on one line should prevent transformation
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                a = 1; self.assertRaises(ValueError, print, 'ok')
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    # no pytest import should be required because transformation should not run
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])


def test_small_statement_not_expr_is_not_transformed():
    # first small-statement not an Expr (e.g., assignment) means no conversion
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                x = 2
                # standalone attribute access, not a Call
                self.assertRaises
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])


def test_expr_value_not_call_is_not_transformed():
    # an Expr whose value is not a Call should not be processed
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                # attribute access instead of call
                self.assertRaises
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])


def test_call_with_insufficient_args_is_not_transformed():
    # functional call with only exception arg should not be converted (len(args) < 2)
    src = textwrap.dedent(
        """
        import unittest

        class T(unittest.TestCase):
            def test_x(self):
                self.assertRaises(ValueError)
        """
    )

    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])
