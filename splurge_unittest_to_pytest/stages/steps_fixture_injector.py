from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import libcst as cst

from ..types import Step, StepResult, ContextDelta

DOMAINS = ["stages", "fixtures", "steps"]


@dataclass
class FindInsertionIndexStep(Step):
    id: str = "steps.fixture_injector.find_insertion_index"
    name: str = "find_insertion_index"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        module = context.get("module")
        insert_idx = 0
        if not isinstance(module, cst.Module):
            return StepResult(delta=ContextDelta(values={"insert_idx": insert_idx}))

        for idx, stmt in enumerate(module.body):
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                expr = stmt.body[0]
                if isinstance(expr, cst.Import):
                    for name in expr.names:
                        if getattr(name.name, "value", None) == "pytest":
                            return StepResult(delta=ContextDelta(values={"insert_idx": idx + 1}))

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

        return StepResult(delta=ContextDelta(values={"insert_idx": insert_idx}))


@dataclass
class InsertNodesStep(Step):
    id: str = "steps.fixture_injector.insert_nodes"
    name: str = "insert_nodes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        module = context.get("module")
        nodes = context.get("fixture_nodes") or []
        insert_idx = context.get("insert_idx") or 0
        if not isinstance(module, cst.Module) or not isinstance(nodes, list) or not nodes:
            return StepResult(delta=ContextDelta(values={"module": module}))

        new_body: list[cst.CSTNode] = list(module.body)
        offset = 0
        for fn in nodes:
            if not isinstance(fn, cst.FunctionDef):
                continue
            pos = insert_idx + offset * 3
            new_body.insert(pos, cst.EmptyLine())
            new_body.insert(pos, cst.EmptyLine())
            new_body.insert(pos + 2, fn)
            offset += 1

        new_module = module.with_changes(body=new_body)
        return StepResult(delta=ContextDelta(values={"module": new_module}))


@dataclass
class NormalizeAndPostprocessStep(Step):
    id: str = "steps.fixture_injector.normalize_and_postprocess"
    name: str = "normalize_and_postprocess"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        module = context.get("module")
        nodes = context.get("fixture_nodes") or []
        if not isinstance(module, cst.Module):
            return StepResult(delta=ContextDelta(values={"module": module}))

        # Normalize spacing: ensure exactly two EmptyLine before top-level defs
        normalized: list[cst.CSTNode] = []
        i = 0
        while i < len(module.body):
            node = module.body[i]
            if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
                while normalized and isinstance(normalized[-1], cst.EmptyLine):
                    normalized.pop()
                normalized.append(cst.EmptyLine())
                normalized.append(cst.EmptyLine())
                normalized.append(node)
                i += 1
            else:
                normalized.append(node)
                i += 1

        new_module = module.with_changes(body=normalized)

        # Post-process newly inserted fixtures to convert self.attr -> attr
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
                        pass
                new_body_list.append(node)

            new_module = new_module.with_changes(body=new_body_list)
        except Exception:
            # best-effort
            pass

        return StepResult(delta=ContextDelta(values={"module": new_module, "needs_pytest_import": True}))


__all__ = [
    "FindInsertionIndexStep",
    "InsertNodesStep",
    "NormalizeAndPostprocessStep",
]
