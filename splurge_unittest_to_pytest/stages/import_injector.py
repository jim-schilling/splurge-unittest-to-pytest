"""Deterministically ensure required imports exist in a module.

This stage inspects the pipeline context for flags such as
``needs_pytest_import`` or a set of ``needs_typing_names`` and
inserts minimal import statements at a deterministic location in the
module (after the docstring or existing imports). The injector avoids
duplicating existing imports and will merge or create a single
``from typing import ...`` statement when typing names are requested.
"""

from __future__ import annotations

from typing import Any
from typing import Optional

import libcst as cst

DOMAINS = ["stages", "imports"]

# Associated domains for this module


def import_injector_stage(context: dict[str, Any]) -> dict[str, Any]:
    """Pipeline stage that ensures required imports exist in the module.

    Inspects context flags (for example ``needs_pytest_import``) and scans
    the module to detect and insert required imports deterministically.
    """

    maybe_module = context.get("module")
    module: Optional[cst.Module] = maybe_module if isinstance(maybe_module, cst.Module) else None
    # If flags are absent, default to adding pytest import to support
    # tests that expect import injector to add pytest for bare modules.
    needs_pytest_val = context.get("needs_pytest_import") if "needs_pytest_import" in context else True
    needs_pytest: bool = bool(needs_pytest_val)
    needs_re: bool = bool(context.get("needs_re_import", False))
    needs_unittest: bool = bool(context.get("needs_unittest_import", False))
    needs_sys: bool = bool(context.get("needs_sys_import", False))
    needs_os: bool = bool(context.get("needs_os_import", False))
    needs_shutil: bool = bool(context.get("needs_shutil_import", False))
    if module is None:
        return {}
    # Defensive detection: if any stage introduced direct 'pytest' usage
    # (e.g., pytest.raises) but failed to set the need flag, detect it by
    # scanning the module source and treat that as requiring the import.
    module_text = getattr(module, "code", "")
    if not needs_pytest and ("pytest." in module_text or "@pytest." in module_text):
        needs_pytest = True
    # Detect leftover references to the unittest module in the generated source
    if not needs_unittest and "unittest." in module_text:
        needs_unittest = True
    # Detect references to sys/os commonly used in skip conditions and env checks
    if not needs_sys and "sys." in module_text:
        needs_sys = True
    if not needs_os and ("os." in module_text or "os.environ" in module_text or "os.getenv" in module_text):
        needs_os = True
    # detect common shutil usage anywhere in the module text
    if not needs_shutil and ("shutil." in module_text or "import shutil" in module_text):
        needs_shutil = True

    # If no stage signaled that pytest or re is required and the caller
    # explicitly provided flags, skip insertion to keep imports minimal.
    # However, when flags are absent (caller didn't set them), we default
    # to inserting pytest to preserve previous behavior and tests.
    if ("needs_pytest_import" in context or "needs_re_import" in context) and not (needs_pytest or needs_re):
        # Caller explicitly provided flags but none are needed; return
        # module unchanged to avoid inserting imports the caller didn't ask for.
        return {"module": module}
    # quick check: detect whether pytest or unittest are already imported.
    # We must not return early here because callers may request typing
    # imports; instead remember which imports exist so we avoid inserting
    # duplicates while still allowing insertion of typing/pathlib imports.
    have_pytest = False
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            expr = stmt.body[0]
            if isinstance(expr, cst.ImportFrom) and getattr(expr.module, "value", None) == "pytest":
                have_pytest = True
            if isinstance(expr, cst.Import):
                # check alias names
                for name in expr.names:
                    if getattr(name.name, "value", None) == "pytest":
                        have_pytest = True
            # also detect if unittest is already imported
            if isinstance(expr, cst.ImportFrom) and getattr(expr.module, "value", None) == "unittest":
                needs_unittest = False
            if isinstance(expr, cst.Import):
                for name in expr.names:
                    if getattr(name.name, "value", None) == "unittest":
                        needs_unittest = False
    # build import node
    import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    re_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("re"))])])
    sys_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("sys"))])])
    os_import_node = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    # decide insertion index: after docstring if present, else after imports, else at 0
    insert_idx = 0
    # find docstring
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
        # find last import
        last_import = -1
        for idx, stmt in enumerate(module.body):
            if (
                isinstance(stmt, cst.SimpleStatementLine)
                and stmt.body
                and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
            ):
                last_import = idx
        if last_import >= 0:
            insert_idx = last_import + 1
        else:
            insert_idx = 0
    new_body = list(module.body)
    # insert imports in a deterministic, human-friendly order. We prefer
    # imports that commonly appear in our goldens first. This list is
    # intentionally small and can be extended as needed.
    preferred_order: list[tuple[str, cst.SimpleStatementLine]] = [
        ("pytest", import_node),
        ("re", re_import_node),
        ("os", os_import_node),
        ("sys", sys_import_node),
        ("tempfile", cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("tempfile"))])])),
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
        to_insert.append(cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("shutil"))])]))

    # Also support insertion of typing names requested by upstream stages.
    # Upstream stages may provide a context key 'needs_typing_names' which
    # should be an iterable of names (e.g., ['Any', 'List']). We'll insert a
    # single `from typing import ...` ImportFrom statement for any missing
    # names, deduplicating against existing typing imports.
    typing_names = context.get("needs_typing_names") or []
    # normalize to set of strings
    typing_needed: set[str] = set()
    for n in typing_names:
        if isinstance(n, str) and n:
            typing_needed.add(n)
    if typing_needed:
        # check existing typing imports to avoid duplicates and locate the existing ImportFrom
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

        # Determine missing typing names (excluding any Path which is special-cased)
        missing = set(typing_needed) - existing_typing
        if "Path" in missing:
            missing.remove("Path")
            # insert pathlib import independently and place it before typing import
            pathlib_import_node = cst.SimpleStatementLine(
                body=[cst.ImportFrom(module=cst.Name("pathlib"), names=[cst.ImportAlias(name=cst.Name("Path"))])]
            )
            # ensure pathlib import is inserted early (we'll place at insert_idx)
            # avoid duplicating pathlib import if it already exists
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
                # Merge missing names into the existing ImportFrom statement in place
                combined = sorted(existing_typing.union(missing))
                typing_import_node = cst.SimpleStatementLine(
                    body=[
                        cst.ImportFrom(
                            module=cst.Name("typing"),
                            names=[cst.ImportAlias(name=cst.Name(n)) for n in combined],
                        )
                    ]
                )
                # Replace the existing statement in the new_body and insert any pending nodes
                new_body = list(module.body)
                new_body[existing_typing_idx] = typing_import_node
                insert_offset = 0
                for node in to_insert:
                    new_body.insert(insert_idx + insert_offset, node)
                    insert_offset += 1

                new_module = module.with_changes(body=new_body)
                return {"module": new_module}
            else:
                # No existing typing import; create a new one and append to to_insert
                typing_import_node = cst.SimpleStatementLine(
                    body=[
                        cst.ImportFrom(
                            module=cst.Name("typing"),
                            names=[cst.ImportAlias(name=cst.Name(n)) for n in missing_list],
                        )
                    ]
                )
                to_insert.append(typing_import_node)

    # Deduplicate by import name to avoid duplicate imports. We'll collect
    # existing import names and skip inserting names already present.
    existing_names: set[str] = set()
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.Import):
                for name in first.names:
                    # name.name is an Identifier node; convert to string
                    existing_names.add(getattr(name.name, "value", ""))
            if isinstance(first, cst.ImportFrom):
                module_name = getattr(first.module, "value", None)
                if module_name:
                    existing_names.add(str(module_name))

    # Insert nodes in an order that keeps our preferred order intact
    # while also appending any less-common imports (like pathlib or typing)
    insert_offset = 0
    # First, build a stable ordering for to_insert: those matching preferred
    # names in our list should appear in that order; the rest appended
    ordered_insert: list[cst.SimpleStatementLine] = []
    preferred_keys = [k for k, _ in preferred_order]

    # pick from to_insert those whose module/name appears in preferred_keys
    def _key_for_node(n: cst.SimpleStatementLine) -> str | None:
        first = n.body[0]
        if isinstance(first, cst.Import):
            if first.names:
                return getattr(first.names[0].name, "value", None)
        if isinstance(first, cst.ImportFrom):
            mod = getattr(first, "module", None)
            if isinstance(mod, cst.Name):
                return mod.value
            # Attribute modules (rare) -> return dotted form
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
    # Ensure pytest (if present) is placed first for canonical ordering
    for key in preferred_keys:
        for node in list(remaining):
            k = _key_for_node(node)
            if k == key:
                ordered_insert.append(node)
                remaining.remove(node)

    # If pytest was not captured above but is present in remaining, move it to front
    for node in list(remaining):
        if _key_for_node(node) == "pytest":
            ordered_insert.insert(0, node)
            remaining.remove(node)

    # Append anything left (pathlib, typing, others) sorted deterministically
    # by their string representation so output is stable.
    remaining_sorted = sorted(remaining, key=lambda n: repr(n))
    ordered_insert.extend(remaining_sorted)

    for node in ordered_insert:
        # pick the import alias name to check for duplication
        name_node = node.body[0]
        insert_name = None
        if isinstance(name_node, cst.Import) and name_node.names:
            insert_name = getattr(name_node.names[0].name, "value", None)
        elif isinstance(name_node, cst.ImportFrom):
            # module can be a Name or an Attribute; convert to dotted string
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

    # Spacing after imports is handled by the tidy stage to avoid duplicate
    # EmptyLine insertions from multiple stages. Do not add EmptyLine sentinels
    # here; tidy will normalize and ensure PEP8-compliant spacing.
    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
