"""TestMethodRewriter stage: rewrite test methods to accept fixtures instead of self/cls.

This stage expects `collector_output` in the context and will remove the
first parameter from test methods if it's `self` or `cls`, then append fixture
parameters inferred from the class's `setup_assignments` keys.
"""
from __future__ import annotations

from typing import Any, Dict, List

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
            # preserve existing params (keep self/cls when present)
            params = list(updated_node.params.params)
            # append fixture params from collector
            class_info = self._classes_map.get(self._current_class)
            if class_info:
                fixtures = list(class_info.setup_assignments.keys())
                for f in fixtures:
                    # avoid duplicates
                    if any(p.name.value == f for p in params):
                        continue
                    params.append(cst.Param(name=cst.Name(f)))
            new_params = updated_node.params.with_changes(params=params)
            return updated_node.with_changes(params=new_params)

    transformer = Rewriter(collector.classes)
    new_module = module.visit(transformer)
    return {"module": new_module}
