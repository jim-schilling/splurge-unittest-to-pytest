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


def _update_test_function(fn: cst.FunctionDef, fixture_names: List[str], remove_self: bool) -> cst.FunctionDef:
    # Remove first param if appropriate (and allowed by module-level unittest usage) and append fixture params (avoid duplicates)
    params = list(fn.params.params)
    if remove_self and _should_remove_first_param(fn):
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

    # Allow configurable setup/teardown name lists via collector output when available
    def _is_setup_name(name: str) -> bool:
        # Collector records canonical setUp names; fall back to common defaults
        return name in ("setUp", "setUpClass")

    def _is_teardown_name(name: str) -> bool:
        return name in ("tearDown", "tearDownClass")

    new_body: List[cst.BaseStatement] = []
    classes = collector.classes

    for stmt in module.body:
        if isinstance(stmt, cst.ClassDef) and stmt.name.value in classes:
            cls_info = classes[stmt.name.value]
            new_class_body: List[cst.BaseStatement] = []
            # per-class fixture names come from setup_assignments keys (stable order)
            fixture_names = list(cls_info.setup_assignments.keys())

            for member in stmt.body.body:
                # preserve non-function members (assign, pass, etc.)
                if not isinstance(member, cst.FunctionDef):
                    new_class_body.append(member)
                    continue

                mname = member.name.value
                # drop only exact setup/teardown functions (avoid accidental removal)
                if _is_setup_name(mname) or _is_teardown_name(mname):
                    # However, if the method has unexpected decorators or a non-empty signature
                    # we conservatively keep it to avoid changing behavior.
                    if member.decorators:
                        new_class_body.append(member)
                        continue
                    # otherwise drop it (assignments are already captured by collector)
                    continue

                # update test functions discovered by collector or named with test* prefix
                if mname.startswith("test") or member in cls_info.test_methods:
                    # Decide per-class whether to remove the first param by checking
                    # if the class originally inherited from unittest.TestCase.
                    def _class_inherits_unittest_testcase(class_node: cst.ClassDef) -> bool:
                        for base in getattr(class_node, 'bases', []) or []:
                            # base is an Arg or similar in some parsers; guard accordingly
                            bval = getattr(base, 'value', base)
                            # unittest.TestCase or TestCase
                            if isinstance(bval, cst.Attribute):
                                if isinstance(bval.value, cst.Name) and bval.value.value == 'unittest' and getattr(bval.attr, 'value', '') == 'TestCase':
                                    return True
                            if isinstance(bval, cst.Name) and bval.value == 'TestCase':
                                return True
                        return False

                    remove_self = _class_inherits_unittest_testcase(cls_info.node)
                    updated_fn = _update_test_function(member, fixture_names, remove_self)
                    new_class_body.append(updated_fn)
                    continue

                # otherwise retain the member unchanged
                new_class_body.append(member)

            new_class = stmt.with_changes(body=stmt.body.with_changes(body=new_class_body))
            new_body.append(new_class)
        else:
            new_body.append(stmt)

    new_module = module.with_changes(body=new_body)
    return {"module": new_module}
