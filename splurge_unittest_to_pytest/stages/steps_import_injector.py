from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast

import libcst as cst

from ..types import Step, StepResult, ContextDelta

DOMAINS = ["stages", "imports", "steps"]


def _get_module(context: Mapping[str, Any]) -> cst.Module | None:
    mod = context.get("module")
    return mod if isinstance(mod, cst.Module) else None


@dataclass
class DetectNeedsStep(Step):
    id: str = "steps.import_injector.detect_needs.core"
    name: str = "detect_needs_core"

    def execute(self, ctx: Mapping[str, Any], resources: Any) -> StepResult:
        mod = _get_module(ctx)
        if mod is None:
            return StepResult(delta=ContextDelta(values={}))
        explicit_pytest_flag = "needs_pytest_import" in ctx
        if explicit_pytest_flag:
            needs_pytest = bool(ctx.get("needs_pytest_import"))
        else:
            has_imports = any(
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
                for stmt in getattr(mod, "body", [])
            )
            needs_pytest = not has_imports

        needs_re = bool(ctx.get("needs_re_import", False))
        needs_unittest = bool(ctx.get("needs_unittest_import", False))
        needs_sys = bool(ctx.get("needs_sys_import", False))
        needs_os = bool(ctx.get("needs_os_import", False))
        needs_shutil = bool(ctx.get("needs_shutil_import", False))

        module_text = getattr(mod, "code", "")
        if not needs_pytest and ("pytest." in module_text or "@pytest." in module_text):
            needs_pytest = True
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
        return StepResult(delta=ContextDelta(values=values))


@dataclass
class InsertImportsStep(Step):
    id: str = "steps.import_injector.insert_imports.core"
    name: str = "insert_imports_core"

    def execute(self, ctx: Mapping[str, Any], resources: Any) -> StepResult:
        mod = _get_module(ctx)
        if mod is None:
            return StepResult(delta=ContextDelta(values={}))
        needs_pytest = bool(ctx.get("needs_pytest_import", False))
        needs_re = bool(ctx.get("needs_re_import", False))
        needs_sys = bool(ctx.get("needs_sys_import", False))
        needs_os = bool(ctx.get("needs_os_import", False))
        needs_shutil = bool(ctx.get("needs_shutil_import", False))

        have_pytest = False
        module_text = getattr(mod, "code", "")
        for stmt in mod.body:
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                expr = stmt.body[0]
                if isinstance(expr, cst.ImportFrom) and getattr(expr.module, "value", None) == "pytest":
                    have_pytest = True
                if isinstance(expr, cst.Import):
                    for name in expr.names:
                        if getattr(name.name, "value", None) == "pytest":
                            have_pytest = True

        if not needs_pytest and ("pytest." in module_text or "@pytest." in module_text):
            needs_pytest = True

        if ("needs_pytest_import" in ctx or "needs_re_import" in ctx) and not (needs_pytest or needs_re):
            return StepResult(delta=ContextDelta(values={"module": mod}))

        import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
        re_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("re"))])])
        sys_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("sys"))])])
        os_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])

        insert_idx = 0
        doc_idx = None
        for idx, stmt in enumerate(mod.body):
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
            first_import_idx = None
            last_import_idx = -1
            for idx, stmt in enumerate(mod.body):
                if (
                    isinstance(stmt, cst.SimpleStatementLine)
                    and stmt.body
                    and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
                ):
                    if first_import_idx is None:
                        first_import_idx = idx
                    last_import_idx = idx
            if needs_pytest:
                insert_idx = 0 if doc_idx is None else doc_idx + 1
            else:
                insert_idx = last_import_idx + 1 if last_import_idx >= 0 else 0

        new_body = list(mod.body)
        preferred_order: list[tuple[str, cst.SimpleStatementLine]] = [
            ("pytest", import_node),
            ("re", re_import_node),
            ("os", os_import_node),
            ("sys", sys_import_node),
            (
                "tempfile",
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("tempfile"))])]),
            ),
            (
                "shutil",
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("shutil"))])]),
            ),
            (
                "subprocess",
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("subprocess"))])]),
            ),
            (
                "json",
                cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("json"))])]),
            ),
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

        typing_names = cast(list, ctx.get("needs_typing_names") or [])
        explicit_typing_flag = "needs_typing_names" in ctx
        typing_needed: set[str] = set()
        for n in typing_names:
            if isinstance(n, str) and n:
                typing_needed.add(n)
        try:
            for candidate in ("Dict", "List", "Tuple", "Optional", "Any", "NamedTuple", "Generator", "Path"):
                if candidate in module_text and candidate not in typing_needed:
                    typing_needed.add(candidate)
        except Exception:
            pass
        if typing_needed:
            existing_typing: set[str] = set()
            existing_typing_idx: int | None = None
            for idx, stmt in enumerate(mod.body):
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
                for stmt in mod.body:
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
                    new_body2 = list(mod.body)
                    new_body2[existing_typing_idx] = typing_import_node
                    insert_offset2 = 0
                    for node in to_insert:
                        new_body2.insert(insert_idx + insert_offset2, node)
                        insert_offset2 += 1
                    new_module2 = mod.with_changes(body=new_body2)
                    return StepResult(delta=ContextDelta(values={"module": new_module2}))
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

        existing_names: set[str] = set()
        for stmt in mod.body:
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
                modx = getattr(first, "module", None)
                if isinstance(modx, cst.Name):
                    return modx.value
                if isinstance(modx, cst.Attribute):
                    parts: list[str] = []
                    cur: cst.BaseExpression | cst.Attribute = modx
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
                mod2 = getattr(name_node, "module", None)
                if isinstance(mod2, cst.Name):
                    insert_name = mod2.value
                elif isinstance(mod2, cst.Attribute):
                    parts: list[str] = []
                    cur: cst.BaseExpression | cst.Attribute = mod2
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

        new_module = mod.with_changes(body=new_body)

        class _NameCollector(cst.CSTVisitor):
            def __init__(self) -> None:
                self.names: set[str] = set()
                self._in_import: int = 0

            def visit_Import(self, node: cst.Import) -> None:
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
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], cst.ImportFrom)
                and getattr(stmt.body[0].module, "value", None) == "typing"
            ):
                if explicit_typing_flag:
                    filtered_body.append(stmt)
                    continue
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
        return StepResult(delta=ContextDelta(values={"module": final_module}))


__all__ = ["DetectNeedsStep", "InsertImportsStep"]
