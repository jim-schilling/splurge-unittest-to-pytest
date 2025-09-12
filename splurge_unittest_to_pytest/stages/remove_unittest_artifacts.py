"""Pipeline stage: remove unittest imports and strip unittest.TestCase inheritance.

This stage ensures that converted modules no longer retain the unittest import
or TestCase base classes which were previously removed by the legacy transformer.
"""
from __future__ import annotations

from typing import Any

import libcst as cst


def remove_unittest_artifacts_stage(context: dict[str, Any]) -> dict[str, Any]:
    module: cst.Module | None = context.get("module")
    if module is None:
        return {"module": module}

    class Cleaner(cst.CSTTransformer):
        def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
            # Remove any top-level import of the unittest module or
            # from unittest import ... statements. We assume the rest of the
            # pipeline converts unittest usages to pytest equivalents.
            new_body: list[cst.BaseStatement] = []
            for stmt in updated_node.body:
                if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                    first = stmt.body[0]
                    # import unittest or from unittest import ...
                    if isinstance(first, cst.Import):
                        skip = False
                        for alias in first.names:
                            name = getattr(alias.name, 'value', '') if hasattr(alias, 'name') else ''
                            if name == 'unittest' or (isinstance(name, str) and name.split('.')[0] == 'unittest'):
                                skip = True
                                break
                        if skip:
                            continue
                    if isinstance(first, cst.ImportFrom) and first.module is not None:
                        if isinstance(first.module, cst.Name) and first.module.value == 'unittest':
                            continue
                new_body.append(stmt)

            return updated_node.with_changes(body=new_body)

        def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
            # filter out bases that are unittest.TestCase or bare TestCase
            if not updated_node.bases:
                return updated_node
            new_bases: list[cst.Arg] = []
            removed = False
            for base in updated_node.bases:
                bval = getattr(base, 'value', base)
                is_unittest_testcase = False
                if isinstance(bval, cst.Attribute):
                    if isinstance(bval.value, cst.Name) and bval.value.value == 'unittest' and getattr(bval.attr, 'value', '') == 'TestCase':
                        is_unittest_testcase = True
                if isinstance(bval, cst.Name) and getattr(bval, 'value', '') == 'TestCase':
                    is_unittest_testcase = True

                if is_unittest_testcase:
                    # remove TestCase base
                    removed = True
                else:
                    new_bases.append(base)

            if removed:
                return updated_node.with_changes(bases=new_bases)
            return updated_node

    new_module = module.visit(Cleaner())
    return {"module": new_module}
