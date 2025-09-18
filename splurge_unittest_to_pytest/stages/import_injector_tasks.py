"""Taskized implementation pieces for the import injector stage (pilot).

Provides two small `CstTask`-style tasks used by `import_injector_stage`:
    - DetectNeedsCstTask: determine which imports are needed based on context and module text
    - InsertImportsCstTask: insert imports deterministically given the needs flags

These tasks are internal to the stage and preserve existing behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast

import libcst as cst

from ..types import Task, TaskResult, ContextDelta


DOMAINS = ["stages", "imports", "tasks"]


def _get_module(context: Mapping[str, Any]) -> cst.Module | None:
    mod = context.get("module")
    return mod if isinstance(mod, cst.Module) else None


@dataclass
class DetectNeedsCstTask(Task):
    id: str = "tasks.import_injector.detect_needs"
    name: str = "detect_needs"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module = _get_module(context)
        if module is None:
            return TaskResult(delta=ContextDelta(values={}))

        # Start from caller-provided flags (if any) to preserve explicit choices.
        # Preserve legacy behavior: only emit the key when explicitly requested
        # or detected by scanning. Do not set a default True in context deltas.
        explicit_pytest_flag = "needs_pytest_import" in context
        needs_pytest = bool(context.get("needs_pytest_import")) if explicit_pytest_flag else False

        needs_re = bool(context.get("needs_re_import", False))
        needs_unittest = bool(context.get("needs_unittest_import", False))
        needs_sys = bool(context.get("needs_sys_import", False))
        needs_os = bool(context.get("needs_os_import", False))
        needs_shutil = bool(context.get("needs_shutil_import", False))

        module_text = getattr(module, "code", "")
        if not needs_pytest and ("pytest." in module_text or "@pytest." in module_text):
            needs_pytest = True
        # Legacy .bak tests expect pytest available when unittest.main pattern is present
        if not needs_pytest and "unittest.main" in module_text:
            needs_pytest = True
        if not needs_unittest and ("unittest." in module_text or "import unittest" in module_text):
            needs_unittest = True
        if not needs_sys and "sys." in module_text:
            needs_sys = True
        if not needs_os and ("os." in module_text or "os.environ" in module_text or "os.getenv" in module_text):
            needs_os = True
        if not needs_shutil and ("shutil." in module_text or "import shutil" in module_text):
            needs_shutil = True

        values: dict[str, Any] = {}
        if explicit_pytest_flag or needs_pytest:
            values["needs_pytest_import"] = needs_pytest
        if needs_re:
            values["needs_re_import"] = True
        if needs_unittest:
            values["needs_unittest_import"] = True
        if needs_sys:
            values["needs_sys_import"] = True
        if needs_os:
            values["needs_os_import"] = True
        if needs_shutil:
            values["needs_shutil_import"] = True
        return TaskResult(delta=ContextDelta(values=values))


@dataclass
class InsertImportsCstTask(Task):
    id: str = "tasks.import_injector.insert_imports"
    name: str = "insert_imports"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module = _get_module(context)
        if module is None:
            return TaskResult(delta=ContextDelta(values={}))

        # Do not default to True when absent; only insert pytest when explicitly
        # requested or when other detectors set the flag earlier.
        needs_pytest = bool(context.get("needs_pytest_import", False))
        needs_re = bool(context.get("needs_re_import", False))
        needs_sys = bool(context.get("needs_sys_import", False))
        needs_os = bool(context.get("needs_os_import", False))
        needs_shutil = bool(context.get("needs_shutil_import", False))

        # quick check of existing imports to avoid duplicates and possibly flip unittest flag
        have_pytest = False
        module_text = getattr(module, "code", "")
        for stmt in module.body:
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                expr = stmt.body[0]
                if isinstance(expr, cst.ImportFrom) and getattr(expr.module, "value", None) == "pytest":
                    have_pytest = True
                if isinstance(expr, cst.Import):
                    for name in expr.names:
                        if getattr(name.name, "value", None) == "pytest":
                            have_pytest = True

        # Defensive detection: if code uses pytest (e.g., @pytest.fixture or pytest.raises),
        # ensure pytest import is requested even if earlier detection missed it.
        if not needs_pytest and ("pytest." in module_text or "@pytest." in module_text):
            needs_pytest = True

        # If explicit flags were provided and neither pytest nor re are needed, keep unchanged
        if ("needs_pytest_import" in context or "needs_re_import" in context) and not (needs_pytest or needs_re):
            return TaskResult(delta=ContextDelta(values={"module": module}))

        # Special-case: when the module has no imports and no explicit flags were provided,
        # default to adding pytest import to satisfy legacy expectations.
        if not ("needs_pytest_import" in context or "needs_re_import" in context):
            has_any_import = any(
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
                for stmt in module.body
            )
            if not has_any_import:
                needs_pytest = True

        import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
        re_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("re"))])])
        sys_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("sys"))])])
        os_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])

        # decide insertion index: after docstring if present, else after imports, else at 0
        insert_idx = 0
        for idx, stmt in enumerate(module.body):
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], cst.Expr)
                and isinstance(stmt.body[0].value, cst.SimpleString)
            ):
                insert_idx = idx + 1
                break
        else:
            last_import = -1
            for idx, stmt in enumerate(module.body):
                if (
                    isinstance(stmt, cst.SimpleStatementLine)
                    and stmt.body
                    and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
                ):
                    last_import = idx
            insert_idx = last_import + 1 if last_import >= 0 else 0

        new_body = list(module.body)
        preferred_order: list[tuple[str, cst.SimpleStatementLine]] = [
            ("pytest", import_node),
            ("re", re_import_node),
            ("os", os_import_node),
            ("sys", sys_import_node),
            (
                "tempfile",
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("tempfile"))])]),
            ),
            ("shutil", cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("shutil"))])])),
            (
                "subprocess",
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("subprocess"))])]),
            ),
            ("json", cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("json"))])])),
        ]

        to_insert: list[cst.SimpleStatementLine] = []
        if needs_pytest and not have_pytest:
            to_insert.append(import_node)
        if needs_re:
            to_insert.append(re_import_node)
        if needs_os:
            to_insert.append(os_import_node)
        if needs_sys:
            to_insert.append(sys_import_node)
        if needs_shutil:
            to_insert.append(
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("shutil"))])])
            )

        # typing names
        typing_names = cast(list, context.get("needs_typing_names") or [])
        typing_needed: set[str] = set()
        for n in typing_names:
            if isinstance(n, str) and n:
                typing_needed.add(n)
        if typing_needed:
            existing_typing: set[str] = set()
            existing_typing_idx: int | None = None
            for idx, stmt in enumerate(module.body):
                if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                    first = stmt.body[0]
                    if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "typing":
                        existing_typing_idx = idx
                        for alias in getattr(first, "names") or []:
                            an = getattr(alias, "name", None)
                            if isinstance(an, cst.Name):
                                existing_typing.add(an.value)

            missing = set(typing_needed) - existing_typing
            if "Path" in missing:
                missing.remove("Path")
                pathlib_import_node = cst.SimpleStatementLine(
                    body=[cst.ImportFrom(module=cst.Name("pathlib"), names=[cst.ImportAlias(name=cst.Name("Path"))])]
                )
                have_pathlib = False
                for stmt in module.body:
                    if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                        first = stmt.body[0]
                        if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "pathlib":
                            have_pathlib = True
                            break
                if not have_pathlib:
                    to_insert.append(pathlib_import_node)

            if missing:
                missing_list = sorted(missing)
                if existing_typing_idx is not None:
                    combined = sorted(existing_typing.union(missing))
                    typing_import_node = cst.SimpleStatementLine(
                        body=[
                            cst.ImportFrom(
                                module=cst.Name("typing"),
                                names=[cst.ImportAlias(name=cst.Name(n)) for n in combined],
                            )
                        ]
                    )
                    new_body = list(module.body)
                    new_body[existing_typing_idx] = typing_import_node
                    insert_offset = 0
                    for node in to_insert:
                        new_body.insert(insert_idx + insert_offset, node)
                        insert_offset += 1
                    new_module = module.with_changes(body=new_body)
                    return TaskResult(delta=ContextDelta(values={"module": new_module}))
                else:
                    typing_import_node = cst.SimpleStatementLine(
                        body=[
                            cst.ImportFrom(
                                module=cst.Name("typing"),
                                names=[cst.ImportAlias(name=cst.Name(n)) for n in missing_list],
                            )
                        ]
                    )
                    to_insert.append(typing_import_node)

        # Deduplicate by import name
        existing_names: set[str] = set()
        for stmt in module.body:
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                first = stmt.body[0]
                if isinstance(first, cst.Import):
                    for name in first.names:
                        existing_names.add(getattr(name.name, "value", ""))
                if isinstance(first, cst.ImportFrom):
                    module_name = getattr(first.module, "value", None)
                    if module_name:
                        existing_names.add(str(module_name))

        insert_offset = 0
        ordered_insert: list[cst.SimpleStatementLine] = []
        preferred_keys = [k for k, _ in preferred_order]

        def _key_for_node(n: cst.SimpleStatementLine) -> str | None:
            first = n.body[0]
            if isinstance(first, cst.Import):
                if first.names:
                    return getattr(first.names[0].name, "value", None)
            if isinstance(first, cst.ImportFrom):
                mod = getattr(first, "module", None)
                if isinstance(mod, cst.Name):
                    return mod.value
                if isinstance(mod, cst.Attribute):
                    parts: list[str] = []
                    cur: cst.BaseExpression | cst.Attribute = mod
                    while isinstance(cur, cst.Attribute):
                        if isinstance(getattr(cur, "attr", None), cst.Name):
                            parts.insert(0, cur.attr.value)
                        cur = cur.value
                    if isinstance(cur, cst.Name):
                        parts.insert(0, cur.value)
                    return ".".join(parts) if parts else None
            return None

        remaining = list(to_insert)
        for key in preferred_keys:
            for node in list(remaining):
                k = _key_for_node(node)
                if k == key:
                    ordered_insert.append(node)
                    remaining.remove(node)
        for node in list(remaining):
            if _key_for_node(node) == "pytest":
                ordered_insert.insert(0, node)
                remaining.remove(node)
        remaining_sorted = sorted(remaining, key=lambda n: repr(n))
        ordered_insert.extend(remaining_sorted)

        for node in ordered_insert:
            name_node = node.body[0]
            insert_name = None
            if isinstance(name_node, cst.Import) and name_node.names:
                insert_name = getattr(name_node.names[0].name, "value", None)
            elif isinstance(name_node, cst.ImportFrom):
                mod = getattr(name_node, "module", None)
                if isinstance(mod, cst.Name):
                    insert_name = mod.value
                elif isinstance(mod, cst.Attribute):
                    parts: list[str] = []
                    cur: cst.BaseExpression | cst.Attribute = mod
                    while isinstance(cur, cst.Attribute):
                        attr_name = getattr(cur.attr, "value", None)
                        if attr_name is not None:
                            parts.insert(0, attr_name)
                        cur = cur.value
                    if isinstance(cur, cst.Name):
                        parts.insert(0, cur.value)
                    insert_name = ".".join(parts) if parts else None
            if insert_name and insert_name in existing_names:
                continue
            new_body.insert(insert_idx + insert_offset, node)
            insert_offset += 1
            if insert_name:
                existing_names.add(str(insert_name))

        new_module = module.with_changes(body=new_body)
        return TaskResult(delta=ContextDelta(values={"module": new_module}))


__all__ = ["DetectNeedsCstTask", "InsertImportsCstTask"]
