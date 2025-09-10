"""Tidy stage: insert EmptyLine separators between top-level fixtures and classes for readability."""
from __future__ import annotations

from typing import Any, Dict, List

import libcst as cst


def tidy_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    module: cst.Module = context.get("module")
    if module is None:
        return {"module": module}
    new_body: List[cst.BaseStatement] = []
    prev_was_fixture = False
    for stmt in module.body:
        is_fixture = isinstance(stmt, cst.FunctionDef) and any(
            isinstance(d.decorator, cst.Attribute) and d.decorator.attr.value == "fixture" for d in getattr(stmt, "decorators", [])
        )
        if prev_was_fixture and not is_fixture:
            # insert an empty line separation
            new_body.append(cst.EmptyLine())
        new_body.append(stmt)
        prev_was_fixture = is_fixture
    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
