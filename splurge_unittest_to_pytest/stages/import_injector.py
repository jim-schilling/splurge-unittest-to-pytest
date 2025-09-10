"""ImportInjector: ensure `import pytest` exists and insert it after module docstring or imports."""
from __future__ import annotations

from typing import Dict, Any

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


def import_injector_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    module: cst.Module = context.get("module")
    collector: CollectorOutput | None = context.get("collector_output")
    needs_pytest: bool = bool(context.get("needs_pytest_import", False))
    needs_re: bool = bool(context.get("needs_re_import", False))
    if module is None:
        return {}
    # If no stage signaled that pytest is required, skip insertion (keeps imports minimal)
    if not needs_pytest and not needs_re:
        return {"module": module}
    # quick check: if module already contains pytest import, do nothing
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            expr = stmt.body[0]
            if isinstance(expr, cst.ImportFrom):
                if getattr(expr.module, "value", None) == "pytest":
                    return {"module": module}
            if isinstance(expr, cst.Import):
                # check alias names
                for name in expr.names:
                    if name.name.value == "pytest":
                        return {"module": module}
    # build import node
    import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    re_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("re"))])])
    # decide insertion index: after docstring if present, else after imports, else at 0
    insert_idx = 0
    # find docstring
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], cst.Expr) and isinstance(stmt.body[0].value, cst.SimpleString):
            insert_idx = idx + 1
            break
    else:
        # find last import
        last_import = -1
        for idx, stmt in enumerate(module.body):
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom)):
                last_import = idx
        if last_import >= 0:
            insert_idx = last_import + 1
        else:
            insert_idx = 0
    new_body = list(module.body)
    # insert imports in a deterministic order: first pytest (if requested), then re (if requested)
    insert_offset = 0
    if needs_pytest:
        new_body.insert(insert_idx + insert_offset, import_node)
        insert_offset += 1
    if needs_re:
        # avoid duplicate if re already present (checked above)
        new_body.insert(insert_idx + insert_offset, re_import_node)
    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
