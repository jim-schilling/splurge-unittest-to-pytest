"""CstTask for removing unittest artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, cast, TYPE_CHECKING

import libcst as cst

from ..types import Task, TaskResult, ContextDelta

if TYPE_CHECKING:
    from ..types import Step


DOMAINS = ["stages", "helpers", "tasks"]


@dataclass
class RemoveUnittestArtifactsTask(Task):
    id: str = "tasks.helpers.remove_unittest_artifacts"
    name: str = "remove_unittest_artifacts"
    steps: Sequence["Step"] = ()

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module: cst.Module | None = context.get("module")
        if module is None:
            return TaskResult(delta=ContextDelta(values={"module": module}))

        class Cleaner(cst.CSTTransformer):
            def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
                new_body: list[Any] = []
                for stmt in updated_node.body:
                    if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                        first_small = stmt.body[0]
                        if isinstance(first_small, cst.Import):
                            skip = False
                            for alias in first_small.names:
                                name = getattr(alias.name, "value", "") if hasattr(alias, "name") else ""
                                if name == "unittest" or (isinstance(name, str) and name.split(".")[0] == "unittest"):
                                    skip = True
                                    break
                            if skip:
                                continue
                        if isinstance(first_small, cst.ImportFrom) and first_small.module is not None:
                            if isinstance(first_small.module, cst.Name) and first_small.module.value == "unittest":
                                continue
                    new_body.append(stmt)

                def _is_main_test(node: cst.BaseExpression) -> bool:
                    if (
                        isinstance(node, cst.Comparison)
                        and isinstance(node.left, cst.Name)
                        and node.left.value == "__name__"
                    ):
                        for comp in getattr(node, "comparisons", []):
                            comparator = getattr(comp, "comparator", None)
                            if isinstance(comparator, cst.SimpleString):
                                sval = comparator.value.strip("\"'")
                                if sval == "__main__":
                                    return True
                            if isinstance(comparator, cst.Name) and comparator.value == "__main__":
                                return True
                    return False

                def _body_calls_main(stmt_block: cst.BaseSuite) -> bool:
                    for s in getattr(stmt_block, "body", []):
                        call_node: cst.Call | None = None
                        if isinstance(s, cst.SimpleStatementLine) and s.body:
                            first_small = s.body[0]
                            if isinstance(first_small, cst.Expr) and isinstance(
                                getattr(first_small, "value", None), cst.Call
                            ):
                                call_node = cast(cst.Call, first_small.value)
                            elif isinstance(first_small, cst.Assign) and isinstance(
                                getattr(first_small, "value", None), cst.Call
                            ):
                                call_node = cast(cst.Call, first_small.value)
                        if call_node is not None:
                            func = getattr(call_node, "func", None)
                            if isinstance(func, cst.Name) and func.value == "main":
                                return True
                            if (
                                isinstance(func, cst.Attribute)
                                and isinstance(getattr(func, "attr", None), cst.Name)
                                and func.attr.value == "main"
                            ):
                                return True
                            for a in getattr(call_node, "args", []) or []:
                                aval = getattr(a, "value", None)
                                if isinstance(aval, cst.Call):
                                    afunc = getattr(aval, "func", None)
                                    if isinstance(afunc, cst.Name) and afunc.value == "main":
                                        return True
                                    if (
                                        isinstance(afunc, cst.Attribute)
                                        and getattr(afunc, "attr", None)
                                        and isinstance(afunc.attr, cst.Name)
                                        and afunc.attr.value == "main"
                                    ):
                                        return True
                        if isinstance(s, cst.If):
                            if _body_calls_main(s.body):
                                return True
                    return False

                collected: list[Any] = []
                for stmt in new_body:
                    try:
                        if isinstance(stmt, cst.If) and _is_main_test(stmt.test) and _body_calls_main(stmt.body):
                            continue
                    except Exception:
                        pass
                    collected.append(stmt)

                final_body: list[cst.BaseStatement] = list(cast(Sequence[cst.BaseStatement], collected))
                return updated_node.with_changes(body=final_body)

            def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
                if not updated_node.bases:
                    return updated_node
                new_bases: list[cst.Arg] = []
                removed = False
                for base in updated_node.bases:
                    bval = getattr(base, "value", base)
                    is_unittest_testcase = False
                    if isinstance(bval, cst.Attribute):
                        if (
                            isinstance(bval.value, cst.Name)
                            and bval.value.value == "unittest"
                            and getattr(bval.attr, "value", "") == "TestCase"
                        ):
                            is_unittest_testcase = True
                    if isinstance(bval, cst.Name) and getattr(bval, "value", "") == "TestCase":
                        is_unittest_testcase = True
                    if is_unittest_testcase:
                        removed = True
                    else:
                        new_bases.append(base)
                if removed:
                    return updated_node.with_changes(bases=new_bases)
                return updated_node

        new_module = module.visit(Cleaner())
        return TaskResult(delta=ContextDelta(values={"module": new_module}))


__all__ = ["RemoveUnittestArtifactsTask"]
