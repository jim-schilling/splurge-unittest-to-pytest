import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def _has_with_nodes(module: cst.Module) -> bool:
    found = False

    class _V(cst.CSTVisitor):
        def visit_With(self, node: cst.With) -> None:
            nonlocal found
            found = True

    module.visit(_V())
    return found


def test_multi_statement_simple_statement_line_is_not_transformed():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x(self):\n                a = 1; self.assertRaises(ValueError, print, 'ok')\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])


def test_small_statement_not_expr_is_not_transformed():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x_02(self):\n                x = 2\n                # standalone attribute access, not a Call\n                self.assertRaises\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])


def test_expr_value_not_call_is_not_transformed():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x_03(self):\n                # attribute access instead of call\n                self.assertRaises\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])


def test_call_with_insufficient_args_is_not_transformed():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x_04(self):\n                self.assertRaises(ValueError)\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_with_nodes(out["module"])
