"""TestMethodRewriter stage: rewrite test methods to accept fixtures instead of self/cls.

This stage expects `collector_output` in the context and will remove the
first parameter from test methods if it's `self` or `cls`, then append fixture
parameters inferred from the class's `setup_assignments` keys.
"""

from __future__ import annotations

from typing import Any, Optional

import libcst as cst
from splurge_unittest_to_pytest.converter.method_params import should_remove_first_param

DOMAINS = ["stages", "rewriter"]

# Associated domains for this module


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
            # build new params: remove leading 'self'/'cls' and append fixture
            # params inferred from the collector's setup_assignments for the
            # current class. Do not change staticmethod signatures.
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

            if not is_static:
                # decide behavior based on whether this class had setup assignments
                fixtures = []
                if self._current_class and self._current_class in self._classes_map:
                    class_info = self._classes_map[self._current_class]
                    fixtures = list(class_info.setup_assignments.keys())

                if fixtures:
                    # class had setup assignments: remove leading self/cls if present
                    if params and should_remove_first_param(original_node):
                        params.pop(0)
                    # append fixture params
                    for fx in fixtures:
                        params.append(cst.Param(name=cst.Name(fx)))
                else:
                    # no fixtures: ensure instance/class methods include self/cls
                    is_classmethod = False
                    for dec in original_node.decorators or []:
                        if isinstance(dec.decorator, cst.Name) and dec.decorator.value == "classmethod":
                            is_classmethod = True
                            break
                    desired_first = cst.Name("cls") if is_classmethod else cst.Name("self")
                    if not params:
                        params.insert(0, cst.Param(name=desired_first))
                    else:
                        first_name = getattr(params[0].name, "value", None)
                        if first_name not in ("self", "cls"):
                            params.insert(0, cst.Param(name=desired_first))

            new_params = updated_node.params.with_changes(params=params)
            return updated_node.with_changes(params=new_params)

    transformer = Rewriter(collector.classes)
    new_module = module.visit(transformer)
    return {"module": new_module}
