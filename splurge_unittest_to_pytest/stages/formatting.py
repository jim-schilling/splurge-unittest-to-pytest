"""Formatting helpers for pipeline stages.

Provides functions to normalize module- and class-level spacing and make
blank-line counts deterministic across stages.
"""

from __future__ import annotations

from typing import Optional, cast, Any

import libcst as cst

DOMAINS = ["stages", "tidy"]


def _node_to_str(node: Optional[cst.BaseExpression] | None) -> str:
    if node is None:
        return ""
    if isinstance(node, cst.Name):
        return node.value
    if isinstance(node, cst.Attribute):
        parts: list[str] = []
        cur: cst.BaseExpression | cst.Attribute = node
        while isinstance(cur, cst.Attribute):
            attr_name = getattr(cur.attr, "value", None)
            if attr_name is not None:
                parts.insert(0, attr_name)
            cur = cur.value
        if isinstance(cur, cst.Name):
            parts.insert(0, cur.value)
        return ".".join(parts)
    return getattr(node, "value", "") or ""


def normalize_class_body(indented: cst.IndentedBlock) -> cst.IndentedBlock:
    """Normalize class body spacing: exactly one blank line between methods.

    Collapse runs of :class:`cst.EmptyLine` within the class body so there
    is at most one blank line between consecutive :class:`cst.FunctionDef`
    members.

    Args:
        indented: The :class:`cst.IndentedBlock` representing the class body.

    Returns:
        A new :class:`cst.IndentedBlock` with normalized spacing.
    """
    members = list(indented.body)
    new_members: list[Any] = []
    i = 0
    while i < len(members):
        m = members[i]
        if isinstance(m, cst.EmptyLine):
            # find end of run
            j = i + 1
            while j < len(members) and isinstance(members[j], cst.EmptyLine):
                j += 1
            prev_non_empty: Any = None
            for k in range(len(new_members) - 1, -1, -1):
                if not isinstance(new_members[k], cst.EmptyLine):
                    prev_non_empty = new_members[k]
                    break
            next_non_empty = members[j] if j < len(members) else None
            if (
                isinstance(prev_non_empty, cst.SimpleStatementLine)
                and prev_non_empty.body
                and isinstance(prev_non_empty.body[0], cst.FunctionDef)
                and isinstance(next_non_empty, cst.FunctionDef)
            ):
                new_members.append(cst.EmptyLine())
            i = j
            continue
        new_members.append(m)
        i += 1

    return indented.with_changes(body=new_members)


def normalize_module(module: cst.Module) -> cst.Module:
    """Normalize module-level spacing and import grouping.

    The function performs several normalization steps:

    - Deduplicate imports and group them (stdlib, thirdparty, local).
    - Ensure exactly two blank lines after the import block when imports are
      present.
    - Collapse runs of :class:`cst.EmptyLine` between top-level definitions to
      two where appropriate.
    - Normalize class bodies using :func:`normalize_class_body`.

    Args:
        module: The :class:`cst.Module` to normalize.

    Returns:
        A new :class:`cst.Module` with spacing and import grouping normalized.
    """
    body = list(module.body)

    # Extract docstring if present
    docstring_node: Any = None
    rest = body
    if body:
        first = body[0]
        if (
            isinstance(first, cst.SimpleStatementLine)
            and first.body
            and isinstance(first.body[0], cst.Expr)
            and isinstance(first.body[0].value, cst.SimpleString)
        ):
            docstring_node = first
            rest = body[1:]

    import_stmts: list[Any] = [
        s
        for s in rest
        if isinstance(s, cst.SimpleStatementLine) and s.body and isinstance(s.body[0], (cst.Import, cst.ImportFrom))
    ]
    other_stmts: list[Any] = [s for s in rest if s not in import_stmts]

    # Deduplicate imports by name
    seen: set[str] = set()
    deduped: list[Any] = []
    for s in import_stmts:
        head = cast(cst.BaseSmallStatement | cst.BaseStatement, s.body[0])
        if isinstance(head, cst.Import):
            name_node = head.names[0].name if head.names else None
            name = _node_to_str(name_node)
        else:
            name = _node_to_str(getattr(head, "module", None))
        if name and name in seen:
            continue
        if name:
            seen.add(name)
        deduped.append(s)

    # Classify imports simply
    stdlib: list[Any] = []
    thirdparty: list[Any] = []
    local: list[Any] = []
    for s in deduped:
        head2 = cast(cst.BaseSmallStatement | cst.BaseStatement, s.body[0])
        if isinstance(head2, cst.Import):
            name_node = head2.names[0].name if head2.names else None
            name = _node_to_str(name_node)
        else:
            name = _node_to_str(getattr(head2, "module", None))
        if "pytest" in name:
            thirdparty.append(s)
        elif "splurge" in name:
            local.append(s)
        else:
            stdlib.append(s)

    new_body: list[Any] = []
    if docstring_node is not None:
        new_body.append(cast(cst.BaseSmallStatement | cst.BaseStatement, docstring_node))

    first_group = True
    for group in (stdlib, thirdparty, local):
        if not group:
            continue
        if not first_group:
            new_body.append(cast(Any, cst.EmptyLine()))
        new_body.extend(group)
        first_group = False

    # ensure exactly two blank lines after import block, but avoid adding
    # them when the following code already starts with the desired spacing.
    if import_stmts:
        # trim trailing empties after the last import group
        while new_body and isinstance(new_body[-1], cst.EmptyLine):
            new_body.pop()

        # If other_stmts already begins with at least two EmptyLine nodes, do
        # not insert additional ones. Otherwise, append two EmptyLine nodes.
        after_imports_prefix: list[cst.EmptyLine] = []
        if other_stmts:
            # look at the leading elements of other_stmts to see existing empties
            for s in other_stmts:
                if isinstance(s, cst.EmptyLine):
                    after_imports_prefix.append(s)
                else:
                    break

        if len(after_imports_prefix) < 2:
            new_body.append(cast(Any, cst.EmptyLine()))
            new_body.append(cast(Any, cst.EmptyLine()))

    # append remaining statements
    new_body.extend(other_stmts)

    # Normalize runs of EmptyLine in module body: decide desired counts
    normalized: list[Any] = []
    i = 0
    while i < len(new_body):
        node = new_body[i]
        if isinstance(node, cst.EmptyLine):
            # count run
            j = i + 1
            while j < len(new_body) and isinstance(new_body[j], cst.EmptyLine):
                j += 1
            prev_non: Any = None
            for k in range(len(normalized) - 1, -1, -1):
                if not isinstance(normalized[k], cst.EmptyLine):
                    prev_non = normalized[k]
                    break
            next_non = new_body[j] if j < len(new_body) else None

            def is_top(n: object | None) -> bool:
                return isinstance(n, (cst.FunctionDef, cst.ClassDef))

            desired = 1
            if is_top(prev_non) or is_top(next_non):
                desired = 2

            for _ in range(desired):
                normalized.append(cast(Any, cst.EmptyLine()))
            i = j
            continue
        # normalize class body spacing
        if isinstance(node, cst.ClassDef):
            node = node.with_changes(body=normalize_class_body(cast(cst.IndentedBlock, node.body)))
            # If the class is followed by other top-level statements, ensure
            # exactly two blank lines after the class in the module body.
            # We'll append the class now, and if the next non-empty is not None
            # we'll push two EmptyLine nodes after it when consuming runs below.
            normalized.append(node)
            # peek ahead to see if next meaningful node exists
            next_idx = i + 1
            # skip existing empties in new_body
            while next_idx < len(new_body) and isinstance(new_body[next_idx], cst.EmptyLine):
                next_idx += 1
            next_non = new_body[next_idx] if next_idx < len(new_body) else None
            if next_non is not None:
                # ensure two blank lines after class
                normalized.append(cast(Any, cst.EmptyLine()))
                normalized.append(cast(Any, cst.EmptyLine()))
            i = next_idx
            continue
        normalized.append(node)
        i += 1

    return module.with_changes(body=normalized)


# Associated domains for this module
