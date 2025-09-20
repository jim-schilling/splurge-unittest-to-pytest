from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from splurge_unittest_to_pytest.converter.method_params import should_remove_first_param

from ..types import ContextDelta, Step, StepResult


@dataclass
class RewriteMethodParamsStep(Step):
    id: str = "steps.rewriter.rewrite_method_params"
    name: str = "rewrite_method_params"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:
        maybe_module = context.get("module")
        module: cst.Module | None = maybe_module if isinstance(maybe_module, cst.Module) else None
        collector = context.get("collector_output")
        if module is None or collector is None:
            return StepResult(delta=ContextDelta(values={}))

        classes_map = getattr(collector, "classes", {})

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

            def leave_FunctionDef(
                self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
            ) -> cst.FunctionDef:
                if self._current_class is None:
                    return updated_node
                name = original_node.name.value
                if not name.startswith("test"):
                    return updated_node
                params = list(updated_node.params.params)
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
                    fixtures: list[str] = []
                    if self._current_class and self._current_class in self._classes_map:
                        class_info = self._classes_map[self._current_class]
                        fixtures = list(getattr(class_info, "setup_assignments", {}).keys())
                    if fixtures:
                        if params and should_remove_first_param(original_node):
                            params.pop(0)
                        for fx in fixtures:
                            params.append(cst.Param(name=cst.Name(fx)))
                    else:
                        desired_first = cst.Name("cls") if is_classmethod else cst.Name("self")
                        if not params:
                            params.insert(0, cst.Param(name=desired_first))
                        else:
                            first_name = getattr(params[0].name, "value", None)
                            if first_name not in ("self", "cls"):
                                params.insert(0, cst.Param(name=desired_first))
                return updated_node.with_changes(params=updated_node.params.with_changes(params=params))

        transformer = Rewriter(classes_map)
        new_module = module.visit(transformer)
        return StepResult(delta=ContextDelta(values={"module": new_module}))


__all__ = ["RewriteMethodParamsStep"]
