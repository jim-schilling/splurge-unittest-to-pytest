from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast

import libcst as cst

from ..types import Step, StepResult, ContextDelta

DOMAINS = ["stages", "imports", "steps"]


def _get_module(context: Mapping[str, Any]) -> cst.Module | None:
    mod = context.get("module")
    return mod if isinstance(mod, cst.Module) else None


def _find_typing_indices(mod: cst.Module) -> list[int]:
    """Return indices of top-level `from typing import` SimpleStatementLine nodes."""
    idxs: list[int] = []
    for idx, stmt in enumerate(mod.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "typing":
                idxs.append(idx)
    return idxs


def _collect_aliases_and_paren(
    mod: cst.Module, typing_indices: list[int]
) -> tuple[list[cst.ImportAlias], set[str], cst.ImportFrom | None, int | None]:
    """Collect unique ImportAlias nodes across typing ImportFroms and prefer a paren source.

    Returns (collected_aliases, seen_names, paren_source, paren_index).
    """
    collected_aliases: list[cst.ImportAlias] = []
    seen: set[str] = set()
    paren_source: cst.ImportFrom | None = None
    paren_index: int | None = None
    for idx in typing_indices:
        stmt = mod.body[idx]
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom):
                if paren_source is None and getattr(first, "lpar", None) is not None:
                    paren_source = first
                    paren_index = idx
                for alias in getattr(first, "names") or []:
                    an = getattr(alias, "name", None)
                    if isinstance(an, cst.Name) and an.value not in seen:
                        collected_aliases.append(alias)
                        seen.add(an.value)
    return collected_aliases, seen, paren_source, paren_index


def _render_stmt_comments(stmt: cst.CSTNode) -> list[str]:
    """Render a single-statement module for a statement and extract comment text per line."""
    comments: list[str] = []
    try:
        rendered_stmt = cast(cst.SimpleStatementLine | cst.BaseCompoundStatement, stmt)
        src = cst.Module(body=[rendered_stmt]).code
    except Exception:
        src = ""
    for line in src.splitlines():
        if "#" in line:
            comment = line[line.index("#") :].strip()
            if comment:
                comments.append(comment)
    return comments


def _collect_preserved_comments(mod: cst.Module, remove_indices: list[int]) -> list[str]:
    preserved_comments: list[str] = []
    for i in sorted(remove_indices):
        try:
            stmt = mod.body[i]
            for comment in _render_stmt_comments(stmt):
                if comment not in preserved_comments:
                    preserved_comments.append(comment)
        except Exception:
            continue
    return preserved_comments


def _merge_typing_into_existing(mod: cst.Module, existing_idx: int, add_names: set[str]) -> cst.Module:
    """Return a new module with typing names merged into the existing typing ImportFrom at existing_idx.

    This helper preserves the original SimpleStatementLine (so comments and trailing whitespace remain)
    and preserves parentheses tokens from the original ImportFrom when present.
    """
    # Validate canonical target
    if existing_idx < 0 or existing_idx >= len(mod.body):
        return mod
    orig_stmt = mod.body[existing_idx]
    orig_first = orig_stmt.body[0] if isinstance(orig_stmt, cst.SimpleStatementLine) and orig_stmt.body else None
    if not isinstance(orig_first, cst.ImportFrom) or getattr(orig_first.module, "value", None) != "typing":
        return mod

    # Find all typing import statement indices so we can consolidate them
    typing_indices = _find_typing_indices(mod)

    # If there is only the canonical typing import, behave as before but still collect aliases
    if not typing_indices:
        return mod

    # collect alias nodes from all typing ImportFrom statements, preserving their nodes
    # and prefer a paren-containing ImportFrom for formatting.
    collected_aliases, seen, paren_source, paren_index = _collect_aliases_and_paren(mod, typing_indices)

    # append any requested add_names not already present
    for n in sorted(add_names):
        if n not in seen:
            collected_aliases.append(cst.ImportAlias(name=cst.Name(n)))
            seen.add(n)

    new_importfrom = cst.ImportFrom(module=cst.Name("typing"), names=collected_aliases)
    # if any original ImportFrom used parentheses, reuse its lpar/rpar to preserve formatting
    if paren_source is not None:
        try:
            new_importfrom = new_importfrom.with_changes(lpar=paren_source.lpar, rpar=paren_source.rpar)
        except Exception:
            pass

    # Build new statement by replacing the canonical statement (existing_idx)
    # Choose canonical index: prefer paren-containing import, else fall back to provided existing_idx
    canonical_idx = paren_index if paren_index is not None else existing_idx
    if canonical_idx is None:
        canonical_idx = typing_indices[0]

    try:
        orig_stmt = mod.body[canonical_idx]
        new_stmt = orig_stmt.with_changes(body=[new_importfrom])
    except Exception:
        new_stmt = cst.SimpleStatementLine(body=[new_importfrom])

    # Replace canonical and remove other typing import statements
    new_body = list(mod.body)
    # set canonical
    new_body[canonical_idx] = new_stmt

    # Gather comments from other typing import statements so we don't lose them.
    remove_indices = [i for i in typing_indices if i != canonical_idx]
    preserved_comments = _collect_preserved_comments(mod, remove_indices)

    # Filter out any preserved comments that are already present on the canonical
    # merged statement to avoid duplicating the same comment both inline and as
    # a leading line.
    try:
        # Inspect the canonical statement's comments before we remove the
        # other typing import statements. At this point new_body[canonical_idx]
        # holds the merged statement we set above, so render its comments and
        # filter out any preserved comments that are already present there to
        # avoid duplication.
        if 0 <= canonical_idx < len(new_body):
            existing_comments_on_canonical = _render_stmt_comments(new_body[canonical_idx])
            preserved_comments = [c for c in preserved_comments if c not in existing_comments_on_canonical]
    except Exception:
        # best-effort: if inspection fails, keep preserved_comments as-is
        pass

    # Remove other typing import statements (do deletions in reverse to keep indices valid)
    for i in sorted(remove_indices, reverse=True):
        try:
            del new_body[i]
        except Exception:
            pass

    # After deletions, the original canonical_idx may have shifted left by the
    # number of removed indices that were before it. Compute the adjusted
    # canonical index so we attach preserved comments to the correct statement.
    shift = sum(1 for i in remove_indices if i < canonical_idx)
    canonical_idx_after = canonical_idx - shift

    # Attach preserved comments as leading_lines on the canonical merged import so
    # we don't change the module body element types (keeps mypy happy).
    try:
        # Ensure the adjusted index is within bounds. Use an Optional typed local
        # variable so we don't assign None to a variable mypy expects to be a
        # statement node.
        target_stmt: cst.SimpleStatementLine | cst.BaseCompoundStatement | None
        if canonical_idx_after < 0 or canonical_idx_after >= len(new_body):
            target_stmt = None
        else:
            target_stmt = new_body[canonical_idx_after]
        if isinstance(target_stmt, cst.SimpleStatementLine) and preserved_comments:
            # Build new leading_lines: preserved comments followed by existing leading_lines
            existing_leading = list(getattr(target_stmt, "leading_lines", []) or [])
            new_leading: list[cst.EmptyLine] = []
            for comment in preserved_comments:
                try:
                    new_leading.append(cst.EmptyLine(comment=cst.Comment(comment)))
                except Exception:
                    continue
            new_leading.extend(existing_leading)
            try:
                # target_stmt is narrowed to SimpleStatementLine above, but mypy may
                # still need a helpful cast here for the with_changes call.
                new_stmt_with_comments = cast(cst.SimpleStatementLine, target_stmt).with_changes(
                    leading_lines=new_leading
                )
                new_body[canonical_idx_after] = new_stmt_with_comments
            except Exception:
                # If we can't attach leading lines for any reason, leave stmt as-is
                pass
    except Exception:
        pass

    return mod.with_changes(body=new_body)


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
        # Do not request typing imports for names the user defines at top-level
        defined_top_names: set[str] = set()
        try:
            for stmt in mod.body:
                # class and function definitions
                if isinstance(stmt, cst.ClassDef):
                    defined_top_names.add(stmt.name.value)
                if isinstance(stmt, cst.FunctionDef):
                    defined_top_names.add(stmt.name.value)
                # simple assignments (x = ...)
                if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                    first = stmt.body[0]
                    if isinstance(first, cst.Assign):
                        for target in first.targets or []:
                            target_node = target.target
                            if isinstance(target_node, cst.Name):
                                defined_top_names.add(target_node.value)
        except Exception:
            defined_top_names = set()

        try:
            for candidate in ("Dict", "List", "Tuple", "Optional", "Any", "NamedTuple", "Generator", "Path"):
                if candidate in module_text and candidate not in typing_needed and candidate not in defined_top_names:
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
                        # Prefer the first encountered typing import as the canonical location
                        # so that any statement-level comments on earlier imports are preserved.
                        if existing_typing_idx is None:
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
                    # Use helper to merge typing names while preserving alias nodes/comments/parentheses
                    merged_mod = _merge_typing_into_existing(mod, existing_typing_idx, set(missing))
                    new_body2 = list(merged_mod.body)
                    insert_offset2 = 0
                    for node in to_insert:
                        new_body2.insert(insert_idx + insert_offset2, node)
                        insert_offset2 += 1
                    new_module2 = merged_mod.with_changes(body=new_body2)
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

        # Consolidate multiple existing `from typing import` statements into one,
        # even if we didn't add new typing names. This keeps the module tidy and
        # avoids duplicate typing import blocks.
        try:
            typing_idxs: list[int] = []
            for idx, stmt in enumerate(new_module.body):
                if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                    first = stmt.body[0]
                    if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "typing":
                        typing_idxs.append(idx)
            if len(typing_idxs) > 1:
                # merge into the first occurrence
                new_module = _merge_typing_into_existing(new_module, typing_idxs[0], set())
        except Exception:
            # best-effort: if consolidation fails, continue with the current module
            pass

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
