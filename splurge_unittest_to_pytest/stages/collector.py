"""Collector stage: read-only visitor that collects facts from a module.

This is intentionally minimal: collect setUp assignments and teardown statements
for each class, plus module docstring index and import info. The goal is to
provide a stable data shape for the next stages.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import libcst as cst
from libcst import matchers as m


@dataclass
class ClassInfo:
    node: cst.ClassDef
    setup_methods: List[cst.FunctionDef] = field(default_factory=list)
    teardown_methods: List[cst.FunctionDef] = field(default_factory=list)
    test_methods: List[cst.FunctionDef] = field(default_factory=list)
    # store list of assigned expressions per attribute to detect multiple assignments
    setup_assignments: Dict[str, List[cst.BaseExpression]] = field(default_factory=dict)
    teardown_statements: List[cst.BaseStatement] = field(default_factory=list)


@dataclass
class CollectorOutput:
    module: cst.Module
    module_docstring_index: Optional[int]
    imports: List[cst.BaseStatement]
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
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
        self._imports: List[cst.BaseStatement] = []

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
                self._imports.append(stmt)

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
                    assign = stmt.body[0]
                    # assign.targets may be a list; we check target attr
                    target = assign.targets[0].target
                    if m.matches(target, m.Attribute(value=m.Name("self"), attr=m.Name())):
                        attr_name = target.attr.value
                        value = assign.value
                        # append assignment to list (support multiple assignments)
                        self._current_class.setup_assignments.setdefault(attr_name, []).append(value)
                        self.output.has_unittest_usage = True
        elif name in ("tearDown", "tearDownClass"):
            self._current_class.teardown_methods.append(node)
            # collect teardown statements as-is
            for stmt in node.body.body:
                self._current_class.teardown_statements.append(stmt)
        elif name.startswith("test"):
            self._current_class.test_methods.append(node)

    def as_output(self) -> CollectorOutput:
        if self.output is None:
            return CollectorOutput(
                module=self._module or cst.Module([]),
                module_docstring_index=self._module_docstring_index,
                imports=self._imports.copy(),
            )
        return self.output
