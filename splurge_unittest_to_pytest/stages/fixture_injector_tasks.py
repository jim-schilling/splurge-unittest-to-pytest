from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, cast as _cast

import logging
import libcst as cst

from ..types import Task, TaskResult, ContextDelta

logger = logging.getLogger(__name__)


def _find_insertion_index(module: cst.Module) -> int:
    for idx, stmt in enumerate(module.body):
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            expr = stmt.body[0]
            if isinstance(expr, cst.Import):
                for name in expr.names:
                    if getattr(name.name, "value", None) == "pytest":
                        return idx + 1
    start_idx = 0
    if module.body:
        first = module.body[0]
        if (
            isinstance(first, cst.SimpleStatementLine)
            and first.body
            and isinstance(first.body[0], cst.Expr)
            and isinstance(first.body[0].value, cst.SimpleString)
        ):
            start_idx = 1
    insert_idx = start_idx
    for idx in range(start_idx, len(module.body)):
        stmt = module.body[idx]
        if (
            isinstance(stmt, cst.SimpleStatementLine)
            and stmt.body
            and isinstance(stmt.body[0], (cst.Import, cst.ImportFrom))
        ):
            insert_idx = idx + 1
            continue
        break
    return insert_idx


@dataclass
class InsertFixtureNodesTask(Task):
    id: str = "tasks.fixture_injector.insert_fixture_nodes"
    name: str = "insert_fixture_nodes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        maybe_module = context.get("module")
        module: cst.Module | None = maybe_module if isinstance(maybe_module, cst.Module) else None
        nodes = context.get("fixture_nodes") or []
        if module is None or not isinstance(nodes, list) or not nodes:
            return TaskResult(delta=ContextDelta(values={"module": module}))

        try:
            names = [
                getattr(n, "name", None) and getattr(n.name, "value", None)
                for n in nodes
                if isinstance(n, cst.FunctionDef)
            ]
        except Exception:
            names = None
        logger.debug("[triage] InsertFixtureNodesTask received %d fixture_nodes: %s", len(nodes), names)

        insert_idx = _find_insertion_index(module)
        # module.body may contain BaseStatement and BaseSmallStatement; keep
        # the combined type for local lists and use casts when passing to
        # APIs that expect a narrower Sequence[cst.BaseStatement].
        new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = list(module.body)
        for offset, fn in enumerate(nodes):
            if not isinstance(fn, cst.FunctionDef):
                continue
            pos = insert_idx + offset * 3
            new_body.insert(pos, _cast(cst.BaseSmallStatement, cst.EmptyLine()))
            new_body.insert(pos, _cast(cst.BaseSmallStatement, cst.EmptyLine()))
            new_body.insert(pos + 2, fn)

        # Normalize: ensure exactly two EmptyLine nodes before each top-level def/class
        normalized: list[cst.BaseStatement | cst.BaseSmallStatement] = []
        i = 0
        while i < len(new_body):
            node = new_body[i]
            if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
                while normalized and isinstance(normalized[-1], cst.EmptyLine):
                    normalized.pop()
                normalized.append(_cast(cst.BaseSmallStatement, cst.EmptyLine()))
                normalized.append(_cast(cst.BaseSmallStatement, cst.EmptyLine()))
                normalized.append(node)
                i += 1
            else:
                normalized.append(node)
                i += 1

        new_module = module.with_changes(body=normalized)
        # Post-process only the newly-inserted fixture functions to ensure any
        # lingering `self.<name>` attributes are converted to simple names.
        # This can occur if earlier stages left attribute forms that refer to
        # the fixture-local binding; convert them here to keep fixture bodies
        # referring to local names (e.g., `resource_instance`) rather than
        # `self.resource_instance`.
        try:
            fixture_names = {n.name.value for n in nodes if isinstance(n, cst.FunctionDef) and getattr(n, "name", None)}

            class _SelfAttrToName(cst.CSTTransformer):
                def leave_Attribute(self, original: cst.Attribute, updated: cst.Attribute) -> cst.BaseExpression:  # type: ignore[override]
                    try:
                        if (
                            isinstance(updated.value, cst.Name)
                            and updated.value.value == "self"
                            and isinstance(updated.attr, cst.Name)
                        ):
                            return cst.Name(updated.attr.value)
                    except Exception:
                        pass
                    return updated

            new_body_list: list[cst.CSTNode] = []
            for node in new_module.body:
                if isinstance(node, cst.FunctionDef) and node.name.value in fixture_names:
                    try:
                        visited_body = node.body.visit(_SelfAttrToName())
                        new_node = node.with_changes(body=visited_body)
                        new_body_list.append(new_node)
                        continue
                    except Exception:
                        # Fall back to appending the original node on error
                        pass
                new_body_list.append(node)
            # new_body_list may contain BaseStatement and BaseSmallStatement;
            # it's safe to pass as the Module.body value which accepts a
            # Sequence[cst.BaseSmallStatement | cst.BaseStatement].
            new_module = new_module.with_changes(body=new_body_list)
        except Exception:
            # Best-effort: do not fail fixture insertion on unexpected errors
            pass

        return TaskResult(delta=ContextDelta(values={"module": new_module, "needs_pytest_import": True}))


__all__ = ["InsertFixtureNodesTask"]
