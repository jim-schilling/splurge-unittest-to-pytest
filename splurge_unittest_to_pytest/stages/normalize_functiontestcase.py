"""Normalize module-level FunctionTestCase(...) call-sites into synthetic ClassDef nodes.

This stage runs early in the pipeline and rewrites module-level assignments like
``testcase = unittest.FunctionTestCase(fn, setUp=init, tearDown=cleanup)`` into a small
``class FunctionTestCase_<name>(unittest.TestCase): ...`` synthetic class so later
stages (collector, fixtures, generator) can operate on a unified representation.

The transformer handles simple aliasing such as ``from unittest import FunctionTestCase as ftc``
and direct names (``FunctionTestCase``) and attribute references (``unittest.FunctionTestCase``).
"""

from __future__ import annotations

from typing import Optional, cast

import libcst as cst
from libcst import matchers as m
from ..converter.helpers import normalize_method_name
from ..types import PipelineContext

DOMAINS = ["stages"]


class _FunctionTestCaseNormalizer(cst.CSTTransformer):
    """Transform module-level assigns that instantiate FunctionTestCase into
    synthetic ClassDef nodes that mimic TestCase classes.

    The synthetic class will have:
      - a placeholder ClassDef name: FunctionTestCase_<target>
      - a test method copied from the provided test function (if possible)
      - setup/teardown methods synthesized from provided setUp/tearDown functions
    """

    def __init__(self) -> None:
        super().__init__()
        # map alias name -> canonical (FunctionTestCase)
        self._name_aliases: dict[str, str] = {}
        # collect module-level helper functions by name for easy lookup
        self._func_map: dict[str, cst.FunctionDef] = {}
        # names consumed (helpers/test callables) to remove from module
        self._names_to_remove: set[str] = set()

    def leave_ImportFrom(self, original: cst.ImportFrom, updated: cst.ImportFrom) -> cst.ImportFrom:
        # track `from unittest import FunctionTestCase as ftc`
        names = getattr(updated, "names", None) or []
        for alias in names:
            aname = getattr(alias, "name", None)
            if not isinstance(aname, cst.Name):
                continue
            imported = aname.value
            asname = getattr(alias, "asname", None)
            if imported == "FunctionTestCase":
                if asname is not None and isinstance(getattr(asname, "name", None), cst.Name):
                    self._name_aliases[getattr(asname, "name").value] = "FunctionTestCase"
                else:
                    self._name_aliases["FunctionTestCase"] = "FunctionTestCase"
        return updated

    def leave_Module(self, original: cst.Module, updated: cst.Module) -> cst.Module:
        # build a map of function defs for lookup
        for stmt in updated.body:
            if isinstance(stmt, cst.FunctionDef):
                self._func_map[stmt.name.value] = stmt

        # allow BaseSmallStatement as well because module.body can contain them
        new_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
        for stmt in updated.body:
            # detect assigns of the form name = <Call to FunctionTestCase>
            if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
                inner = stmt.body[0]
                if isinstance(inner, cst.Assign):
                    assign = inner
                    # only top-level simple name target
                    tgt = assign.targets[0].target
                    if not isinstance(tgt, cst.Name):
                        new_body.append(stmt)
                        continue
                    val = assign.value
                    if not isinstance(val, cst.Call):
                        new_body.append(stmt)
                        continue

                    # determine callee name
                    callee = val.func
                    callee_name: Optional[str] = None
                    if isinstance(callee, cst.Attribute) and isinstance(callee.attr, cst.Name):
                        callee_name = callee.attr.value
                    elif isinstance(callee, cst.Name):
                        callee_name = callee.value

                    if callee_name is None:
                        new_body.append(stmt)
                        continue

                    resolved = self._name_aliases.get(callee_name, callee_name)
                    if resolved != "FunctionTestCase":
                        new_body.append(stmt)
                        continue

                    # Extract args: first positional is the test callable; keywords setUp/tearDown
                    test_fn_name: Optional[str] = None
                    setup_name: Optional[str] = None
                    teardown_name: Optional[str] = None
                    if val.args:
                        # first positional arg is test callable expression
                        first = val.args[0]
                        fc = getattr(first, "value", None)
                        # if it's a Name, record it
                        if isinstance(fc, cst.Name):
                            test_fn_name = fc.value
                    for a in val.args:
                        kw = getattr(a, "keyword", None)
                        kwname = getattr(kw, "value", None) if kw is not None else None
                        if kwname == "setUp":
                            v = getattr(a, "value", None)
                            if isinstance(v, cst.Name):
                                setup_name = v.value
                        if kwname == "tearDown":
                            v = getattr(a, "value", None)
                            if isinstance(v, cst.Name):
                                teardown_name = v.value

                    # Build synthetic ClassDef. Prefer human-readable TestSomething
                    # derived from the callable name when possible.
                    if test_fn_name and test_fn_name.startswith("test"):
                        base = test_fn_name[len("test") :]
                        if base:
                            class_base = base[0].upper() + base[1:]
                            synth_name = f"Test{class_base}"
                        else:
                            synth_name = f"FunctionTestCase_{tgt.value}"
                    else:
                        synth_name = f"FunctionTestCase_{tgt.value}"
                    members: list[cst.BaseStatement] = []

                    # Add setup method if setup_name present -> create def setUp(self):
                    # Convert module-level assignments (e.g., _resource = createResource())
                    # into self._resource = createResource() so the Collector recognizes
                    # attribute assignments inside setUp.
                    if setup_name and setup_name in self._func_map:
                        fn = self._func_map[setup_name]
                        new_stmts: list[cst.BaseStatement] = []
                        # collect names assigned in the original setup helper so
                        # we can remove corresponding module-level placeholders
                        # (e.g., `_resource = None`).
                        setup_assigned_names: list[str] = []
                        for st in fn.body.body:
                            # Skip module-level `global` statements entirely - we want
                            # instance attributes on self, not module globals in setUp.
                            if isinstance(st, cst.SimpleStatementLine) and isinstance(st.body[0], cst.Global):
                                continue

                            # handle simple Assign statements assigning to a Name
                            if m.matches(
                                st,
                                m.SimpleStatementLine(body=[m.Assign(targets=[m.AssignTarget(target=m.Name())])]),
                            ):
                                assign = cast(cst.Assign, cast(cst.SimpleStatementLine, st).body[0])
                                target = assign.targets[0].target
                                if isinstance(target, cst.Name):
                                    # create self.<name> = <value>
                                    attr = cst.Attribute(value=cst.Name("self"), attr=cst.Name(target.value))
                                    new_assign = cst.Assign(targets=[cst.AssignTarget(target=attr)], value=assign.value)
                                    new_stmts.append(
                                        cast(cst.BaseStatement, cst.SimpleStatementLine(body=[new_assign]))
                                    )
                                    continue
                            # keep other statements as-is
                            new_stmts.append(cast(cst.BaseStatement, st))

                        params = cst.Parameters(params=[cst.Param(name=cst.Name("self"))])
                        setup_member = cst.FunctionDef(
                            name=cst.Name("setUp"), params=params, body=cst.IndentedBlock(body=new_stmts)
                        )
                        members.append(setup_member)
                        # extract simple Name targets from original setup fn for removal
                        for st in fn.body.body:
                            if m.matches(
                                st, m.SimpleStatementLine(body=[m.Assign(targets=[m.AssignTarget(target=m.Name())])])
                            ):
                                assign = cast(cst.Assign, cast(cst.SimpleStatementLine, st).body[0])
                                target = assign.targets[0].target
                                if isinstance(target, cst.Name):
                                    setup_assigned_names.append(target.value)
                        for n in setup_assigned_names:
                            self._names_to_remove.add(n)

                    # Add teardown method and rewrite references to module-level names
                    # into self.<name> so cleanup references the instance attribute.
                    if teardown_name and teardown_name in self._func_map:
                        fn = self._func_map[teardown_name]
                        # build a transformer to replace Name('x') -> Attribute(self, 'x') for
                        # any names assigned in the setup function

                        class _ToSelfRef(cst.CSTTransformer):
                            def __init__(self, names: list[str]) -> None:
                                super().__init__()
                                self.names = set(names)

                            def leave_Name(self, original: cst.Name, updated: cst.Name) -> cst.BaseExpression:
                                if original.value in self.names:
                                    return cst.Attribute(value=cst.Name("self"), attr=cst.Name(original.value))
                                return updated

                        # for teardown, apply transformer to each stmt
                        new_td_stmts: list[cst.BaseStatement] = []
                        # compute assigned names from setup_member if present
                        # fallback: derive from teardown fn body names (conservative)
                        setup_assigned: list[str] = []
                        for mbr in members:
                            if isinstance(mbr, cst.FunctionDef) and mbr.name.value == "setUp":
                                for s in mbr.body.body:
                                    if m.matches(
                                        s,
                                        m.SimpleStatementLine(
                                            body=[
                                                m.Assign(
                                                    targets=[
                                                        m.AssignTarget(
                                                            target=m.Attribute(value=m.Name("self"), attr=m.Name())
                                                        )
                                                    ]
                                                )
                                            ]
                                        ),
                                    ):
                                        # extract attr name
                                        assign = cast(cst.Assign, cast(cst.SimpleStatementLine, s).body[0])
                                        targ = assign.targets[0].target
                                        if isinstance(targ, cst.Attribute) and isinstance(targ.attr, cst.Name):
                                            setup_assigned.append(targ.attr.value)

                        # If no setup_assigned found, try to find Name targets in original setup fn
                        if not setup_assigned and setup_name and setup_name in self._func_map:
                            sfn = self._func_map[setup_name]
                            for s in sfn.body.body:
                                if m.matches(
                                    s, m.SimpleStatementLine(body=[m.Assign(targets=[m.AssignTarget(target=m.Name())])])
                                ):
                                    assign = cast(cst.Assign, cast(cst.SimpleStatementLine, s).body[0])
                                    target = assign.targets[0].target
                                    if isinstance(target, cst.Name):
                                        setup_assigned.append(target.value)

                        td_transformer = _ToSelfRef(setup_assigned)
                        for st in fn.body.body:
                            try:
                                rv = st.visit(td_transformer)
                                new_td_stmts.append(cast(cst.BaseStatement, rv))
                            except Exception:
                                new_td_stmts.append(cast(cst.BaseStatement, st))

                        params = cst.Parameters(params=[cst.Param(name=cst.Name("self"))])
                        teardown_member = cst.FunctionDef(
                            name=cst.Name("tearDown"), params=params, body=cst.IndentedBlock(body=new_td_stmts)
                        )
                        members.append(teardown_member)

                    # Add test method from callable function if available. Normalize
                    # to snake_case test method name (e.g., testSomething -> test_something)
                    if test_fn_name and test_fn_name in self._func_map:
                        fn = self._func_map[test_fn_name]
                        test_method_name = normalize_method_name(fn.name.value)
                        if not test_method_name.startswith("test"):
                            test_method_name = f"test_{test_method_name}"
                        params = cst.Parameters(params=[cst.Param(name=cst.Name("self"))])
                        test_member = cst.FunctionDef(name=cst.Name(test_method_name), params=params, body=fn.body)
                        members.append(test_member)

                    # mark consumed helper/test names for removal from original module
                    if setup_name:
                        self._names_to_remove.add(setup_name)
                    if teardown_name:
                        self._names_to_remove.add(teardown_name)
                    if test_fn_name:
                        self._names_to_remove.add(test_fn_name)

                    classdef = cst.ClassDef(
                        name=cst.Name(synth_name),
                        bases=[cst.Arg(value=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("TestCase")))],
                        body=cst.IndentedBlock(body=members),
                    )
                    new_body.append(classdef)
                    # omit original assign (drop the FunctionTestCase call)
                    continue

            # default: keep statement
            new_body.append(stmt)

        # Remove any original function defs or simple module-level assigns that
        # were consumed into the synthetic class. This avoids leaving behind
        # module-level placeholders like `_resource = None` when the
        # attribute becomes `self._resource` inside the synthesized class.
        filtered_body: list[cst.BaseStatement | cst.BaseSmallStatement] = []
        for s in new_body:
            # drop consumed function defs
            if (
                isinstance(s, cst.FunctionDef)
                and getattr(s, "name", None) is not None
                and s.name.value in self._names_to_remove
            ):
                continue

            # drop simple module-level Assign statements where the single target
            # is a Name that was consumed into the class (e.g., `_resource = None`).
            if isinstance(s, cst.SimpleStatementLine) and s.body:
                inner = s.body[0]
                if isinstance(inner, cst.Assign):
                    tgt = inner.targets[0].target
                    if isinstance(tgt, cst.Name) and tgt.value in self._names_to_remove:
                        # skip this module-level assign
                        continue

            filtered_body.append(s)
        return updated.with_changes(body=filtered_body)


def normalize_functiontestcase_stage(context: PipelineContext) -> PipelineContext:
    """Pipeline stage function: expects 'module' in context and returns updated context."""
    module = context.get("module")
    if module is None:
        return context
    try:
        transformer = _FunctionTestCaseNormalizer()
        new_mod = module.visit(transformer)
        return {**context, "module": new_mod}
    except Exception:
        # be conservative: on error, return the original context
        return context


__all__ = ["normalize_functiontestcase_stage"]
