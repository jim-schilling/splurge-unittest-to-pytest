from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, cast

import libcst as cst

from ..types import Step, StepResult, ContextDelta

DOMAINS = ["stages", "fixtures", "steps"]


@dataclass
class CollectClassesStep(Step):
    id: str = "steps.fixtures_stage.collect_classes"
    name: str = "collect_classes"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        module = context.get("module")
        collector = context.get("collector_output")
        if module is None or collector is None:
            return StepResult(delta=ContextDelta(values={"module": module}))

        classes = collector.classes if hasattr(collector, "classes") else {}
        return StepResult(delta=ContextDelta(values={"classes": classes}))


@dataclass
class BuildTopLevelFnsStep(Step):
    id: str = "steps.fixtures_stage.build_top_level_fns"
    name: str = "build_top_level_fns"

    def execute(self, context: Mapping[str, Any], resources: Any) -> StepResult:  # type: ignore[override]
        module: Optional[cst.Module] = context.get("module")
        classes = context.get("classes") or {}
        collector = context.get("collector_output")
        if module is None or collector is None:
            return StepResult(delta=ContextDelta(values={"module": module}))

        new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
        for stmt in module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value in classes:
                cls_info = classes[stmt.name.value]
                raw_fixture_names = list(cls_info.setup_assignments.keys())
                fixture_names = [n.lstrip("_") for n in raw_fixture_names]

                for member in stmt.body.body:
                    if not isinstance(member, cst.FunctionDef):
                        continue
                    mname = member.name.value
                    if not (mname.startswith("test") or member in cls_info.test_methods):
                        continue

                    # rewrite self.attr -> attr
                    class _SelfAttrRewriter(cst.CSTTransformer):
                        def leave_Attribute(
                            self, original: cst.Attribute, updated: cst.Attribute
                        ) -> cst.BaseExpression:
                            if (
                                isinstance(original.value, cst.Name)
                                and original.value.value == "self"
                                and isinstance(original.attr, cst.Name)
                            ):
                                return cst.Name(original.attr.value)
                            return updated

                    new_body_block = member.body.visit(_SelfAttrRewriter())
                    params_list = [cst.Param(name=cst.Name(fname)) for fname in fixture_names]
                    params = cst.Parameters(params=params_list)
                    top_fn = cst.FunctionDef(
                        name=cst.Name(mname), params=params, body=cast(cst.BaseSuite, new_body_block), decorators=[]
                    )
                    new_body.append(top_fn)
            else:
                new_body.append(stmt)

        new_module = module.with_changes(body=new_body)
        return StepResult(delta=ContextDelta(values={"module": new_module}))


__all__ = ["CollectClassesStep", "BuildTopLevelFnsStep"]
