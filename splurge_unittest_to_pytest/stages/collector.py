"""Collect class-level setUp/tearDown and module metadata.

This visitor inspects a parsed :class:`libcst.Module` and records
information required by downstream stages: top-level imports, the
module docstring index, discovered classes and their ``setUp``,
``tearDown``, and ``test`` methods, plus simple assignments inside
``setUp`` methods used to infer fixture values.

The collected data is exposed via :class:`CollectorOutput` for later
stages to consume.

Publics:
    Collector, CollectorOutput, ClassInfo

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, cast, Sequence, Any

import libcst as cst
from libcst import matchers as m

DOMAINS = ["stages"]


def _collect_names_from_expr(expr: Any) -> set[str]:
    refs: set[str] = set()

    class _RefCollector(cst.CSTVisitor):
        def visit_Name(self, node: cst.Name) -> None:
            refs.add(node.value)

    try:
        if expr is not None:
            expr.visit(_RefCollector())
    except Exception:
        # be conservative on unexpected shapes
        pass
    return refs


@dataclass
class ClassInfo:
    node: cst.ClassDef
    setup_methods: list[Any] = field(default_factory=list)
    teardown_methods: list[Any] = field(default_factory=list)
    test_methods: list[Any] = field(default_factory=list)
    # store list of assigned expressions per attribute to detect multiple assignments
    setup_assignments: dict[str, list[Any]] = field(default_factory=dict)

    # track simple local assignments inside setUp (e.g., sql_file, schema_file = helper(...))

    local_assignments: dict[str, Any] = field(default_factory=dict)
    teardown_statements: list[Any] = field(default_factory=list)
    # For synthetic entries created from FunctionTestCase, store the
    # original test callable (FunctionDef or Name) so later stages can
    # synthesize a top-level test function directly from it.
    synthetic_test_callable: Optional[Any] = None
    # When synthesized from a FunctionTestCase, record the source setUp
    # and tearDown function names so downstream stages can remove the
    # original helper functions from the module body.
    synthetic_setup_name: Optional[str] = None
    synthetic_teardown_name: Optional[str] = None
    # module-level variable names assigned in setup functions (raw form
    # like '_resource') so we can drop placeholder assignments after
    # creating fixtures.
    raw_setup_vars: list[str] = field(default_factory=list)


@dataclass
class CollectorOutput:
    module: cst.Module
    module_docstring_index: Optional[int]
    imports: Sequence[Any]
    classes: dict[str, ClassInfo] = field(default_factory=dict)
    has_unittest_usage: bool = False


class Collector(cst.CSTVisitor):
    """Collect information about classes, setUp/tearDown, and assignments.

    Usage:
        wrapper = cst.MetadataWrapper(module)
        visitor = Collector()
        wrapper.visit(visitor)
        result = visitor.output
    """

    def __init__(self, normalize_names: bool = False) -> None:
        self.output: Optional[CollectorOutput] = None
        self._current_class: Optional[ClassInfo] = None
        self._module: Optional[cst.Module] = None
        self._module_docstring_index: Optional[int] = None
        self._imports: list[Any] = []
        # map simple alias names to canonical names (e.g., 'ftc' -> 'FunctionTestCase')
        self._name_aliases: dict[str, str] = {}
        # honor raw names by default; can be overridden by pipeline context
        self._normalize_names: bool = bool(normalize_names)
        # mapping of raw attr name -> final used name (when normalization applied)
        self._normalized_map: dict[str, str] = {}

    def visit_Module(self, node: cst.Module) -> None:
        self._module = node
        # find docstring index if present
        for idx, stmt in enumerate(node.body):
            if m.matches(stmt, m.SimpleStatementLine(body=[m.Expr(m.SimpleString())])):
                self._module_docstring_index = idx
                break
        # collect top-level imports and build simple alias mapping for
        # imported names like `from unittest import FunctionTestCase as ftc`.
        for stmt in node.body:
            if m.matches(stmt, m.Import() | m.ImportFrom()):
                self._imports.append(cast(Any, stmt))
                # process ImportFrom to map aliases for FunctionTestCase
                if m.matches(stmt, m.ImportFrom()):
                    imp = cast(Any, stmt)
                    # imp.module may be an Attribute or Name; we only need the
                    # imported names and their asnames.
                    names = getattr(imp, "names", None) or []
                    for alias in names:
                        # alias.name may be a Name node
                        aname = getattr(alias, "name", None)
                        if not isinstance(aname, cst.Name):
                            continue
                        imported = aname.value
                        asname = getattr(alias, "asname", None)
                        if imported == "FunctionTestCase":
                            if asname is not None and isinstance(getattr(asname, "name", None), cst.Name):
                                self._name_aliases[getattr(asname, "name").value] = "FunctionTestCase"
                            else:
                                # direct import: FunctionTestCase -> map the same
                                self._name_aliases["FunctionTestCase"] = "FunctionTestCase"

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        name = node.name.value
        self._current_class = ClassInfo(node=node)
        self.output = self.output or CollectorOutput(
            module=self._module or cst.Module([]),
            module_docstring_index=self._module_docstring_index,
            imports=self._imports.copy(),
        )
        self.output.classes[name] = self._current_class

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self._current_class = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        if self._current_class is None:
            return
        name = node.name.value
        if name in ("setUp", "setUpClass"):
            self._current_class.setup_methods.append(node)
            # collect assignments inside
            for stmt in node.body.body:
                # look for simple self.attr = <expr>
                if m.matches(stmt, m.SimpleStatementLine(body=[m.Assign()])):
                    assign = cast(cst.Assign, cast(cst.SimpleStatementLine, stmt).body[0])
                    # assign.targets may be a list; we check target attr
                    target = assign.targets[0].target
                    # be defensive: target can be many shapes; extract attr if present
                    attr_node = getattr(target, "attr", None)
                    if (
                        isinstance(target, cst.Attribute)
                        and isinstance(attr_node, cst.Name)
                        and isinstance(getattr(target, "value", None), cst.Name)
                        and getattr(getattr(target, "value", None), "value", None) == "self"
                    ):
                        raw_attr_name = attr_node.value
                        # Determine final attribute name according to normalize flag.
                        if self._normalize_names:
                            base = raw_attr_name.lstrip("_") or raw_attr_name
                            # deterministic disambiguation: append _1, _2... if needed
                            candidate = base
                            idx = 1
                            # avoid colliding with existing setup keys or previously normalized values
                            while candidate in self._current_class.setup_assignments or candidate in set(
                                self._normalized_map.values()
                            ):
                                candidate = f"{base}_{idx}"
                                idx += 1
                            attr_name = candidate
                            self._normalized_map[raw_attr_name] = attr_name
                        else:
                            attr_name = raw_attr_name
                        value = assign.value
                        # append assignment to list (support multiple assignments)
                        self._current_class.setup_assignments.setdefault(attr_name, []).append(value)
                        if self.output is not None:
                            self.output.has_unittest_usage = True
                        # record raw name as well for downstream removal/mapping
                        self._current_class.raw_setup_vars.append(raw_attr_name)
                    else:
                        # capture simple local name assignments like `x = helper(...)` or
                        # tuple unpacking `a, b = helper(...)` so we can trace helper
                        # call origins later when converting self.attr placeholders.
                        # target can be Name or Tuple
                        if isinstance(target, cst.Name):
                            lname = target.value
                            # record the assigned expression and a placeholder
                            # index for simple names. Also collect referenced
                            # names inside the RHS so later stages can detect
                            # fixture dependencies (e.g., Path(temp_dir)).
                            refs = _collect_names_from_expr(assign.value)
                            self._current_class.local_assignments[lname] = (assign.value, None, refs)
                        elif isinstance(target, cst.Tuple):
                            # tuple of names -> map each name to (value, index)
                            elements = getattr(target, "elements", []) or []
                            for idx, el in enumerate(elements):
                                inner = getattr(el, "value", None)
                                if isinstance(inner, cst.Name):
                                    refs = _collect_names_from_expr(assign.value)
                                    # tuple element: store index and refs
                                    self._current_class.local_assignments[inner.value] = (assign.value, idx, refs)
        elif name in ("tearDown", "tearDownClass"):
            self._current_class.teardown_methods.append(node)
            # collect teardown statements as-is
            for stmt in node.body.body:
                self._current_class.teardown_statements.append(stmt)
        elif name.startswith("test"):
            self._current_class.test_methods.append(node)

    def visit_Assign(self, node: cst.Assign) -> None:
        """Detect module-level assignments that create a FunctionTestCase instance.

        Patterns handled:
        - `testcase = unittest.FunctionTestCase(fn, setUp=init, tearDown=cleanup)`
        - `testcase = FunctionTestCase(fn, setUp=init, tearDown=cleanup)`
        - `testcase = ftc(fn, setUp=init, tearDown=cleanup)` where `ftc` is an alias
        """
        # only interested in top-level assigns
        if self._current_class is not None:
            return
        # target must be a simple name (we don't need the left-hand name)
        if not isinstance(node.targets[0].target, cst.Name):
            return
        value = node.value
        # look for a Call
        if not isinstance(value, cst.Call):
            return
        # identify callee name (could be Attribute or Name)
        callee = value.func
        callee_name = None
        if isinstance(callee, cst.Attribute):
            # e.g., unittest.FunctionTestCase or ut.FunctionTestCase
            attr = getattr(callee, "attr", None)
            if isinstance(attr, cst.Name):
                callee_name = attr.value
        elif isinstance(callee, cst.Name):
            callee_name = callee.value

        # resolve simple aliases (e.g., ftc -> FunctionTestCase)
        if callee_name in self._name_aliases:
            callee_name = self._name_aliases[callee_name]

        # only proceed if this is a FunctionTestCase call
        if callee_name != "FunctionTestCase":
            return

        # At this point we have a FunctionTestCase(...) call; extract setup/teardown kw
        setup_fn = None
        teardown_fn = None
        # positional[0] is the test function
        if value.args:
            # first arg is the test callable; we can extract its name if needed
            first_arg = value.args[0]
            # record the callable expression (may be a Name or a Lambda/Func)
            test_callable_node = getattr(first_arg, "value", None)
        # libcst.Call stores arguments in .args as Arg nodes which may have
        # a .keyword (Name) or be positional. Iterate safely.
        for a in value.args:
            kw = getattr(a, "keyword", None)
            kwname = getattr(kw, "value", None) if kw is not None else None
            if kwname == "setUp":
                setup_fn = getattr(a.value, "value", None) if isinstance(a.value, cst.Name) else None
            if kwname == "tearDown":
                teardown_fn = getattr(a.value, "value", None) if isinstance(a.value, cst.Name) else None

        # create a synthetic ClassInfo entry to hold normalized data
        synth_name = f"FunctionTestCase_{getattr(node.targets[0].target, 'value', 'anon')}"
        synth = ClassInfo(node=cst.ClassDef(name=cst.Name(synth_name), body=cst.IndentedBlock([])))
        # attach the discovered test callable so downstream stages can emit
        # a top-level test function when no ClassDef is present.
        try:
            synth.synthetic_test_callable = test_callable_node
        except Exception:
            synth.synthetic_test_callable = None

        # remember original setup/teardown names for downstream cleanup
        synth.synthetic_setup_name = setup_fn
        synth.synthetic_teardown_name = teardown_fn

        # locate module-level function defs by name and extract information
        if setup_fn and isinstance(self._module, cst.Module):
            for stmt in self._module.body:
                if m.matches(stmt, m.FunctionDef(name=m.Name(setup_fn))):
                    func = cast(cst.FunctionDef, stmt)
                    # reuse existing collection logic: inspect assign stmts in function body
                    for st in func.body.body:
                        if m.matches(st, m.SimpleStatementLine(body=[m.Assign()])):
                            assign = cast(cst.Assign, cast(cst.SimpleStatementLine, st).body[0])
                            target = assign.targets[0].target
                            # module-level assignment to _resource -> map attribute name
                            if isinstance(target, cst.Name):
                                # treat module-level variable like an attribute name
                                raw = target.value
                                if hasattr(self, "_normalize_names") and self._normalize_names:
                                    base = raw.lstrip("_") or raw
                                    candidate = base
                                    idx = 1
                                    while candidate in synth.setup_assignments or candidate in set(
                                        self._normalized_map.values()
                                    ):
                                        candidate = f"{base}_{idx}"
                                        idx += 1
                                    name = candidate
                                    # record mapping for downstream stages
                                    self._normalized_map[raw] = name
                                else:
                                    name = raw
                                synth.setup_assignments.setdefault(name, []).append(assign.value)
                                # record raw var for later removal
                                synth.raw_setup_vars.append(raw)
                    # mark as unittest usage
                    if self.output is not None:
                        self.output.has_unittest_usage = True
        if teardown_fn and isinstance(self._module, cst.Module):
            for stmt in self._module.body:
                if m.matches(stmt, m.FunctionDef(name=m.Name(teardown_fn))):
                    func = cast(cst.FunctionDef, stmt)
                    for st in func.body.body:
                        synth.teardown_statements.append(st)

        # register synthetic class info in output
        self.output = self.output or CollectorOutput(
            module=self._module or cst.Module([]),
            module_docstring_index=self._module_docstring_index,
            imports=self._imports.copy(),
        )
        self.output.classes[synth_name] = synth
        # mark usage
        self.output.has_unittest_usage = True

    def as_output(self) -> CollectorOutput:
        """Return a populated :class:`CollectorOutput`.

        If nothing has been collected, returns an empty-but-typed
        :class:`CollectorOutput` so downstream stages can rely on a stable
        shape.
        """

        if self.output is None:
            return CollectorOutput(
                module=self._module or cst.Module([]),
                module_docstring_index=self._module_docstring_index,
                imports=self._imports.copy(),
            )
        return self.output


# Associated domains for this module
