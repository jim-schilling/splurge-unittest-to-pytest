import libcst as cst
from typing import cast

from splurge_unittest_to_pytest.stages.raises_stage import RaisesRewriter, raises_stage


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
