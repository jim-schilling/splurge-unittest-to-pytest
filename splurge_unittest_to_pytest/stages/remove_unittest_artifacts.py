"""Pipeline stage: remove unittest imports and strip unittest.TestCase inheritance.

This stage ensures that converted modules no longer retain the unittest import
or TestCase base classes which were previously removed by the legacy transformer.
"""

from __future__ import annotations

from typing import Any, cast, Sequence

import libcst as cst

DOMAINS = ["stages", "helpers"]

# Associated domains for this module


def remove_unittest_artifacts_stage(context: dict[str, Any]) -> dict[str, Any]:
    module: cst.Module | None = context.get("module")
    if module is None:
        return {"module": module}

    class Cleaner(cst.CSTTransformer):
        def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
            # Remove any top-level import of the unittest module or
            # from unittest import ... statements. We assume the rest of the
            # pipeline converts unittest usages to pytest equivalents.
            new_body: list[Any] = []
            for stmt in updated_node.body:
                if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                    first_small = stmt.body[0]
                    # import unittest or from unittest import ...
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

            # Additionally, remove common `if __name__ == '__main__'` guards that
            # call unittest.main() or similar runner helpers to avoid running
            # tests when pytest imports the module.
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
                    # try to extract a Call from common small-statement wrappers
                    call_node: cst.Call | None = None
                    if isinstance(s, cst.SimpleStatementLine) and s.body:
                        first_small = s.body[0]
                        if isinstance(first_small, cst.Expr) and isinstance(
                            getattr(first_small, "value", None), cst.Call
                        ):
                            # mypy thinks first_small.value is BaseExpression; cast after isinstance
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
                        # Also detect nested main calls passed as arguments, e.g.
                        # sys.exit(unittest.main()) where call_node.args contains a Call
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
                        # skip this guard entirely
                        continue
                except Exception:
                    pass
                collected.append(stmt)

            # mypy/typeshed variance: ensure we pass Sequence[BaseStatement]
            final_body: list[cst.BaseStatement] = list(cast(Sequence[cst.BaseStatement], collected))

            return updated_node.with_changes(body=final_body)

        def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
            # filter out bases that are unittest.TestCase or bare TestCase
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
                    # remove TestCase base
                    removed = True
                else:
                    new_bases.append(base)

            if removed:
                return updated_node.with_changes(bases=new_bases)
            return updated_node

    new_module = module.visit(Cleaner())
    return {"module": new_module}
