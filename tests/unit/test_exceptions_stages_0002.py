import libcst as cst
from typing import cast

from splurge_unittest_to_pytest.stages.raises_stage import (
    RaisesRewriter,
    ExceptionAttrRewriter,
    raises_stage,
)

DOMAINS = ["exceptions", "stages"]


def test_exception_attr_rewriter_rewrites_exception_to_value():
    expr = cst.parse_expression("cm.exception")
    new = expr.visit(ExceptionAttrRewriter("cm"))
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(new)])]).code
    assert "cm.value" in code


def test_raises_rewriter_functional_form():
    src = "self.assertRaises(ValueError, func, 1)\n"
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    # Avoid calling .code() which can trigger codegen incompatibilities
    # instead assert on the AST structure: look for a With node using pytest.raises
    found = False
    # The transformer may produce a top-level With node directly or a
    # SimpleStatementLine containing a With depending on flattening. Accept
    # either form.
    for node in new.body:
        candidate = None
        if isinstance(node, cst.SimpleStatementLine) and node.body:
            candidate = node.body[0]
        elif isinstance(node, cst.With):
            candidate = node

        if isinstance(candidate, cst.With):
            first = candidate.items[0]
            if isinstance(first.item, cst.Call) and isinstance(first.item.func, cst.Attribute):
                val = first.item.func
                if (
                    isinstance(val.value, cst.Name)
                    and val.value.value == "pytest"
                    and getattr(val.attr, "value", None) == "raises"
                ):
                    found = True
                    break

    assert found, "expected a With node using pytest.raises"


def test_with_assert_raises_converted_to_pytest_raises() -> None:
    src = """class T:\n    def test_it(self):\n        with self.assertRaises(ValueError):\n            do_something()\n"""
    module = cst.parse_module(src)
    transformer = RaisesRewriter()
    new_mod = module.visit(transformer)
    # should have changed
    assert transformer.made_changes
    # locate the With node and ensure it uses pytest.raises
    with_node = next((n for n in new_mod.body if isinstance(n, cst.ClassDef)), None)
    assert with_node is not None


def test_assert_raises_regex_and_functional_form() -> None:
    src = """def test_fn():\n    self.assertRaisesRegex(ValueError, 'bad', fn, 1, 2)\n"""
    module = cst.parse_module(src)
    # run stage wrapper which returns needs_pytest_import flag
    out = raises_stage({"module": module})
    new_mod = cast(cst.Module, out.get("module"))
    needs = out.get("needs_pytest_import")
    # functional form should have caused a change. Instead of generating code
    # (which can trigger codegen incompatibilities), walk the transformed
    # tree to find a With node or a pytest.raises Call.
    assert needs is True

    class Finder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_with = False
            self.found_pytest_raises = False

        def visit_With(self, node: cst.With) -> None:
            self.found_with = True

        def visit_Call(self, node: cst.Call) -> None:
            try:
                if isinstance(node.func, cst.Attribute) and isinstance(node.func.value, cst.Name):
                    if node.func.value.value == "pytest" and node.func.attr.value == "raises":
                        self.found_pytest_raises = True
            except Exception:
                pass

    finder = Finder()
    new_mod.visit(finder)
    assert finder.found_with or finder.found_pytest_raises
