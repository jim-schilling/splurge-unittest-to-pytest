"""Fixtures stage: remove class setUp/tearDown methods and add fixture params to tests.

This stage consumes `collector_output` (CollectorOutput) and `fixture_specs` produced
by the `generator_stage`. It removes the class-level setup/teardown methods and
updates test method signatures to remove instance/class first params and add
fixture parameters (one per setup attribute) so tests receive the generated fixtures.
"""
from __future__ import annotations

from typing import Dict, Any, List

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput


def _should_remove_first_param(node: cst.FunctionDef) -> bool:
    # Determine if the first parameter should be removed (self/cls).
    if not node.params.params:
        return False
    first = node.params.params[0]
    first_name = getattr(first.name, "value", "")
    # If decorated as staticmethod, don't remove
    for dec in node.decorators or []:
        if isinstance(dec.decorator, cst.Name) and dec.decorator.value == "staticmethod":
            return False
    # If decorated as classmethod, only remove if first param is 'cls'
    for dec in node.decorators or []:
        if isinstance(dec.decorator, cst.Name) and dec.decorator.value == "classmethod":
            return first_name == "cls"
    # Default: remove if first param is 'self'
    return first_name == "self"


def _update_test_function(fn: cst.FunctionDef, fixture_names: List[str]) -> cst.FunctionDef:
    # Remove first param if appropriate and append fixture params (avoid duplicates)
    params = list(fn.params.params)
    if _should_remove_first_param(fn):
        params = params[1:]

    existing = {p.name.value for p in params}
    for name in fixture_names:
        if name in existing:
            continue
        params.append(cst.Param(name=cst.Name(name)))
        existing.add(name)

    new_params = fn.params.with_changes(params=params)
    return fn.with_changes(params=new_params)


def fixtures_stage(context: Dict[str, Any]) -> Dict[str, Any]:
    module: cst.Module | None = context.get("module")
    collector: CollectorOutput | None = context.get("collector_output")
    fixture_specs: Dict[str, Any] = context.get("fixture_specs") or {}
    compat: bool = context.get("compat", False)

    if module is None or collector is None:
        return {"module": module}

    new_body: List[cst.BaseStatement] = []
    # For quick lookup of classes to update
    classes = collector.classes

    for stmt in module.body:
        # only transform ClassDef nodes that were collected
        if isinstance(stmt, cst.ClassDef) and stmt.name.value in classes:
            cls_info = classes[stmt.name.value]
            new_class_body: List[cst.BaseStatement] = []
            # per-class fixture names come from setup_assignments keys
            fixture_names = list(cls_info.setup_assignments.keys())

            for member in stmt.body.body:
                # remove setUp / setUpClass / tearDown / tearDownClass
                if isinstance(member, cst.FunctionDef) and member.name.value in ("setUp", "setUpClass", "tearDown", "tearDownClass"):
                    # drop these methods; their assignments are used to create fixtures
                    continue

                # update test functions (use collector test_methods to be conservative)
                if isinstance(member, cst.FunctionDef) and (member in cls_info.test_methods or member.name.value.startswith("test")):
                    updated_fn = _update_test_function(member, fixture_names)
                    new_class_body.append(updated_fn)
                    continue

                # otherwise keep as-is
                new_class_body.append(member)

            new_class = stmt.with_changes(body=stmt.body.with_changes(body=new_class_body))
            new_body.append(new_class)
        else:
            new_body.append(stmt)

    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
