"""TestMethodRewriter stage: rewrite test methods to accept fixtures instead of self/cls.

This stage expects `collector_output` in the context and will remove the
first parameter from test methods if it's `self` or `cls`, then append fixture
parameters inferred from the class's `setup_assignments` keys.
"""
from __future__ import annotations

from typing import Any, Dict

import libcst as cst


def rewriter_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    module: cst.Module = context.get("module")
    collector = context.get("collector_output")
    if module is None or collector is None:
        return {"module": module}

    class Rewriter(cst.CSTTransformer):
        def __init__(self, classes_map: Dict[str, Any]) -> None:
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
            # Do NOT append fixture parameters to test methods here.
            # The pipeline now inserts an autouse fixture that deterministically
            # retrieves fixture values and attaches them to the instance via
            # request.getfixturevalue(...). Keeping test signatures runnable by
            # default (preserving `self`/`cls`) ensures converted code can be
            # executed as plain Python without requiring pytest to call methods.
            new_params = updated_node.params.with_changes(params=params)
            return updated_node.with_changes(params=new_params)

    transformer = Rewriter(collector.classes)
    new_module = module.visit(transformer)
    return {"module": new_module}
