from typing import cast

import libcst as cst

from splurge_unittest_to_pytest.stages.raises_stage import ExceptionAttrRewriter, RaisesRewriter, raises_stage


def test_rewrites_cm_exception_to_value_when_as_used():
    src = "\nclass T:\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError('msg')\n        # access\n        e = cm.exception\n"
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "with pytest.raises(ValueError) as cm:" in code
    assert "cm.value" in code


def test_exception_attr_rewriter_rewrites_exception_to_value():
    expr = cst.parse_expression("cm.exception")
    new = expr.visit(ExceptionAttrRewriter("cm"))
    code = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(new)])]).code
    assert "cm.value" in code


def test_raises_rewriter_functional_form():
    src = "self.assertRaises(ValueError, func, 1)\n"
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    found = False
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
                    and (getattr(val.attr, "value", None) == "raises")
                ):
                    found = True
                    break
    assert found, "expected a With node using pytest.raises"


def test_with_assert_raises_converted_to_pytest_raises() -> None:
    src = "class T:\n    def test_it(self):\n        with self.assertRaises(ValueError):\n            do_something()\n"
    module = cst.parse_module(src)
    transformer = RaisesRewriter()
    new_mod = module.visit(transformer)
    assert transformer.made_changes
    with_node = next((n for n in new_mod.body if isinstance(n, cst.ClassDef)), None)
    assert with_node is not None


def test_assert_raises_regex_and_functional_form() -> None:
    src = "def test_fn():\n    self.assertRaisesRegex(ValueError, 'bad', fn, 1, 2)\n"
    module = cst.parse_module(src)
    out = raises_stage({"module": module})
    new_mod = cast(cst.Module, out.get("module"))
    needs = out.get("needs_pytest_import")
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


def test_rewrites_cm_exception_to_value_for_as_name():
    src = "\nclass T:\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError('msg')\n        # access\n        e = cm.exception\n"
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "with pytest.raises(ValueError) as cm:" in code
    assert "cm.value" in code


def test_rewrites_in_nested_function_and_comprehension():
    src = "\nclass T:\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError('msg')\n        def inner():\n            return cm.exception\n        vals = [cm.exception for _ in range(1)]\n        f = lambda: cm.exception\n"
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "cm.value" in code
    assert "return cm.value" in code or "cm.value for" in code


def test_does_not_rewrite_when_name_shadowed_in_inner_scopes():
    src = "\nclass T:\n    def test_it(self):\n        with self.assertRaises(ValueError) as cm:\n            raise ValueError('msg')\n        def inner(cm):\n            # this parameter should shadow outer cm and keep .exception\n            return cm.exception\n        vals = [ (lambda cm: cm.exception)(cm) for cm in [cm] ]\n        f = lambda cm: cm.exception\n"
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "with pytest.raises(ValueError) as cm:" in code
    assert "return cm.exception" in code
    assert "lambda cm: cm.exception" in code
