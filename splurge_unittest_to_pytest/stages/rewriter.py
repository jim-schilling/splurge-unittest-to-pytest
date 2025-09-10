"""TestMethodRewriter stage: rewrite test methods to accept fixtures instead of self/cls.

This stage expects `collector_output` in the context and will remove the
first parameter from test methods if it's `self` or `cls`, then append fixture
parameters inferred from the class's `setup_assignments` keys.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import libcst as cst


def rewriter_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    collector = context.get("collector_output")
    if module is None or collector is None:
        return {"module": module}

    class Rewriter(cst.CSTTransformer):
        def __init__(self, classes_map: dict[str, Any]) -> None:
            super().__init__()
            self._current_class: str | None = None
            self._classes_map = classes_map

        def visit_ClassDef(self, node: cst.ClassDef) -> None:
            self._current_class = node.name.value

        def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
            self._current_class = None
            return updated_node

        def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
            # only rewrite methods inside classes
            if self._current_class is None:
                return updated_node
            name = original_node.name.value
            if not name.startswith("test"):
                return updated_node
            # build new params: ensure instance methods inside classes include
            # `self` as the first parameter (or `cls` for @classmethod). Do not
            # add/remove params for @staticmethod methods.
            params = list(updated_node.params.params)
            # detect staticmethod/classmethod decorators on the original node
            is_static = False
            is_classmethod = False
            for dec in original_node.decorators or []:
                if isinstance(dec.decorator, cst.Name):
                    if dec.decorator.value == "staticmethod":
                        is_static = True
                        break
                    if dec.decorator.value == "classmethod":
                        is_classmethod = True
            # If it's a staticmethod, leave params as-is.
            if not is_static:
                desired_first = cst.Name("cls") if is_classmethod else cst.Name("self")
                if not params:
                    # no params; insert desired first param
                    params.insert(0, cst.Param(name=desired_first))
                else:
                    first_name = getattr(params[0].name, 'value', None)
                    if first_name not in ("self", "cls"):
                        # insert desired first param before existing params
                        params.insert(0, cst.Param(name=desired_first))
            # Under Option A we've removed self/cls from test method signatures
            # earlier in the pipeline; here we also rewrite references inside
            # the test body like `self.attr` -> `attr` so test code uses the
            # fixture names directly.
            new_params = updated_node.params.with_changes(params=params)

                # Replace self.attr occurrences with bare fixture names when the
                # original class inherited from unittest.TestCase. The check for
                # unittest.TestCase inheritance uses the class node stored in the
                # collector; no local assignment is required here.
            def _class_inherits_unittest_testcase(class_info: Any) -> bool:
                node = getattr(class_info, 'node', None)
                if node is None:
                    return False
                for base in getattr(node, 'bases', []) or []:
                    bval = getattr(base, 'value', base)
                    if isinstance(bval, cst.Attribute):
                        if isinstance(bval.value, cst.Name) and bval.value.value == 'unittest' and getattr(bval.attr, 'value', '') == 'TestCase':
                            return True
                    if isinstance(bval, cst.Name) and bval.value == 'TestCase':
                        return True
                return False

            # Do not rewrite `self.attr` -> `attr`. Keep methods runnable
            # by retaining instance attribute access; fixtures are appended
            # as parameters but autouse attach will also set instance attrs
            # when running under pytest.
            return updated_node.with_changes(params=new_params)

    transformer = Rewriter(collector.classes)
    new_module = module.visit(transformer)
    return {"module": new_module}
