"""Collector visitor that extracts class-level setup/teardown metadata.

This visitor inspects a parsed :class:`libcst.Module` and records
information required by downstream stages: top-level imports, the
module docstring index, discovered classes and their ``setUp``/
``tearDown``/``test`` methods, and simple assignments inside ``setUp``
methods used to infer fixture values.

The collected data is exposed via :class:`CollectorOutput` for later
stages to consume.
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

    def __init__(self) -> None:
        self.output: Optional[CollectorOutput] = None
        self._current_class: Optional[ClassInfo] = None
        self._module: Optional[cst.Module] = None
        self._module_docstring_index: Optional[int] = None
        self._imports: list[Any] = []

    def visit_Module(self, node: cst.Module) -> None:
        self._module = node
        # find docstring index if present
        for idx, stmt in enumerate(node.body):
            if m.matches(stmt, m.SimpleStatementLine(body=[m.Expr(m.SimpleString())])):
                self._module_docstring_index = idx
                break
        # collect top-level imports
        for stmt in node.body:
            if m.matches(stmt, m.Import() | m.ImportFrom()):
                self._imports.append(cast(Any, stmt))

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
                        attr_name = attr_node.value
                        value = assign.value
                        # append assignment to list (support multiple assignments)
                        self._current_class.setup_assignments.setdefault(attr_name, []).append(value)
                        if self.output is not None:
                            self.output.has_unittest_usage = True
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
