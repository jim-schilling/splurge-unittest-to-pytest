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
        # Legacy compatibility: when the caller did not explicitly provide a
        # pytest flag, default to requesting a pytest import so converted
        # modules have pytest available by default. If the caller did set
        # the flag, honor its boolean value.
        explicit_pytest_flag = "needs_pytest_import" in context
        if explicit_pytest_flag:
            needs_pytest = bool(context.get("needs_pytest_import"))
        else:
            # Default to requesting pytest only for modules that currently
            # have no imports. This preserves legacy behavior for empty
            # modules while avoiding forcing pytest into modules that
            # already import other libraries (like os, sys).
            has_imports = any(
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
                for stmt in getattr(module, "body", [])
            )
            needs_pytest = not has_imports

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

        # Legacy behavior previously defaulted to adding `import pytest` for
        # modules with no imports when no explicit flags were provided. That
        # was noisy and caused pytest to be added to empty/whitespace-only
        # files. Rely on explicit flags (e.g., earlier stages setting
        # `needs_pytest_import`) or on detected usages in the module text
        # instead. Do not inject pytest simply because the module has no
        # imports.

        import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
        re_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("re"))])])
        sys_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("sys"))])])
        os_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])

        # decide insertion index: after docstring if present, else after imports, else at 0
        insert_idx = 0
        doc_idx = None
        for idx, stmt in enumerate(module.body):
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], cst.Expr)
                and isinstance(stmt.body[0].value, cst.SimpleString)
            ):
                doc_idx = idx
                break
        if doc_idx is not None:
            insert_idx = doc_idx + 1
        else:
            # find first import index; by default we'll insert after existing imports
            first_import_idx = None
            last_import_idx = -1
            for idx, stmt in enumerate(module.body):
                if (
                    isinstance(stmt, cst.SimpleStatementLine)
                    and stmt.body
                    and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
                ):
                    if first_import_idx is None:
                        first_import_idx = idx
                    last_import_idx = idx

            # If pytest is requested, prefer to insert it at the very top of the
            # module (after docstring if present) so it appears before other
            # imports and matches golden file ordering.
            if needs_pytest:
                insert_idx = 0 if doc_idx is None else doc_idx + 1
            else:
                insert_idx = last_import_idx + 1 if last_import_idx >= 0 else 0

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
        explicit_typing_flag = "needs_typing_names" in context
        typing_needed: set[str] = set()
        for n in typing_names:
            if isinstance(n, str) and n:
                typing_needed.add(n)
        # Heuristic: if the module text references common typing names
        # that weren't explicitly requested, add them so imports like
        # `from typing import Dict` are injected when annotations use them.
        # This helps when upstream stages didn't explicitly record the
        # typing name but the converted code contains it (e.g., `-> Dict`).
        try:
            for candidate in ("Dict", "List", "Tuple", "Optional", "Any", "NamedTuple", "Generator", "Path"):
                if candidate in module_text and candidate not in typing_needed:
                    typing_needed.add(candidate)
        except Exception:
            pass
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

        # Do not reorder imports here; leave grouping/ordering to the
        # formatting stage so that import positions remain deterministic
        # and stable across pipeline runs.

        # If typing imports were added but their names are not referenced
        # in the module, remove them to avoid noisy stdlib imports like
        # `from typing import Any, Generator` when not used. However, if the
        # caller explicitly requested typing names via the context key
        # `needs_typing_names`, preserve the typing import even if it's
        # not referenced in the module text.
        class _NameCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.names: set[str] = set()
                self._in_import: int = 0

            def visit_Import(self, node: cst.Import) -> None:
                # mark entering import so child Names aren't counted
                self._in_import += 1

            def leave_Import(self, node: cst.Import) -> None:
                self._in_import -= 1

            def visit_ImportFrom(self, node: cst.ImportFrom) -> None:
                self._in_import += 1

            def leave_ImportFrom(self, node: cst.ImportFrom) -> None:
                self._in_import -= 1

            def visit_Name(self, node: cst.Name) -> None:
                if self._in_import:
                    return
                self.names.add(node.value)

        collector = _NameCollector()
        try:
            new_module.visit(collector)
        except Exception:
            collector.names = set()

        used_names = collector.names
        filtered_body: list[cst.CSTNode] = []
        for stmt in new_module.body:
            # remove typing imports whose aliases are unused
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], cst.ImportFrom)
                and getattr(stmt.body[0].module, "value", None) == "typing"
            ):
                # If typing names were explicitly requested, keep the import.
                if explicit_typing_flag:
                    filtered_body.append(stmt)
                    continue
                # stmt.body[0].names may be an ImportStar or a sequence of
                # ImportAlias nodes; handle the ImportStar case explicitly
                import_names_obj = stmt.body[0].names
                if isinstance(import_names_obj, (list, tuple)):
                    names = [getattr(n.name, "value", "") for n in import_names_obj or []]
                else:
                    names = []
                keep = any(n and n in used_names for n in names)
                if not keep:
                    continue
            filtered_body.append(stmt)

        final_module = new_module.with_changes(body=filtered_body)
        return TaskResult(delta=ContextDelta(values={"module": final_module}))


__all__ = ["DetectNeedsCstTask", "InsertImportsCstTask"]
