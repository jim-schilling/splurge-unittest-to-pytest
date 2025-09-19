"""CstTask units for fixtures_stage (Stage-4 decomposition).

Tasks:
  - BuildTopLevelTestsTask: produce top-level pytest test functions from classes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, cast

import libcst as cst

from ..types import Task, TaskResult, ContextDelta
from .collector import CollectorOutput
from splurge_unittest_to_pytest.converter.method_params import (
    is_classmethod,
    is_staticmethod,
    first_param_name,
)


DOMAINS = ["stages", "fixtures", "tasks"]


def _update_test_function(
    fn: cst.FunctionDef,
    fixture_names: Sequence[str],
    remove_first: bool,
) -> cst.FunctionDef:
    params = list(fn.params.params)
    if not is_staticmethod(fn):
        if remove_first:
            if params:
                fname = first_param_name(fn)
                if fname in ("self", "cls"):
                    params = params[1:]
        else:
            desired_first = cst.Name("cls") if is_classmethod(fn) else cst.Name("self")
            f_name = first_param_name(fn)
            if f_name not in ("self", "cls"):
                params.insert(0, cst.Param(name=desired_first))
    if remove_first:
        for fname in fixture_names:
            params.append(cst.Param(name=cst.Name(fname)))
    new_params = fn.params.with_changes(params=params)
    return fn.with_changes(params=new_params)


@dataclass
class BuildTopLevelTestsTask(Task):
    id: str = "tasks.fixtures_stage.build_top_level_tests"
    name: str = "build_top_level_tests"

    def execute(self, context: Mapping[str, Any], resources: Any) -> TaskResult:  # type: ignore[override]
        module: Optional[cst.Module] = context.get("module")
        collector: Optional[CollectorOutput] = context.get("collector_output")
        if module is None or collector is None:
            return TaskResult(delta=ContextDelta(values={"module": module}))

        new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
        classes = collector.classes
        for stmt in module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value in classes:
                cls_info = classes[stmt.name.value]
                # Use normalized fixture parameter names (strip leading
                # underscores) so test function signatures match created
                # fixture function names which are generated without
                # leading underscores.
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
        return TaskResult(delta=ContextDelta(values={"module": new_module}))


__all__ = ["BuildTopLevelTestsTask"]
