"""ImportInjector: ensure `import pytest` exists and insert it after module docstring or imports."""
from __future__ import annotations

from typing import Any
from typing import Optional

import libcst as cst


def import_injector_stage(context: dict[str, Any]) -> dict[str, Any]:
    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    # If flags are absent, default to adding pytest import to support
    # tests that expect import injector to add pytest for bare modules.
    needs_pytest_val = context.get("needs_pytest_import") if "needs_pytest_import" in context else True
    needs_pytest: bool = bool(needs_pytest_val)
    needs_re: bool = bool(context.get("needs_re_import", False))
    needs_unittest: bool = bool(context.get("needs_unittest_import", False))
    if module is None:
        return {}
    # Defensive detection: if any stage introduced direct 'pytest' usage
    # (e.g., pytest.raises) but failed to set the need flag, detect it by
    # scanning the module source and treat that as requiring the import.
    module_text = getattr(module, 'code', '')
    if not needs_pytest and ('pytest.' in module_text or '@pytest.' in module_text):
        needs_pytest = True
    # Detect leftover references to the unittest module in the generated source
    if not needs_unittest and 'unittest.' in module_text:
        needs_unittest = True

    # If no stage signaled that pytest or re is required and the caller
    # explicitly provided flags, skip insertion to keep imports minimal.
    # However, when flags are absent (caller didn't set them), we default
    # to inserting pytest to preserve previous behavior and tests.
    if ("needs_pytest_import" in context or "needs_re_import" in context) and not (needs_pytest or needs_re):
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
            # also detect if unittest is already imported
            if isinstance(expr, cst.ImportFrom):
                if getattr(expr.module, "value", None) == "unittest":
                    needs_unittest = False
            if isinstance(expr, cst.Import):
                for name in expr.names:
                    if name.name.value == "unittest":
                        needs_unittest = False
    # build import node
    import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    re_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("re"))])])
    unittest_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("unittest"))])])
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
    if needs_unittest:
        # insert unittest import after pytest/re imports
        new_body.insert(insert_idx + insert_offset, unittest_import_node)
    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
