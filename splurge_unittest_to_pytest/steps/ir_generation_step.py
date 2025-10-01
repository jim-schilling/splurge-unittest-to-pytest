#!/usr/bin/env python3
"""IR generation steps for converting CST to an intermediate representation.

This module provides a pipeline step that analyzes Python ``libcst`` modules
to produce the project's intermediate representation (IR). The IR makes it
easier for downstream transformers and validators to reason about test
structures (imports, classes, fixtures, assertions).

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from pathlib import Path
from typing import Any

import libcst as cst

from ..context import PipelineContext
from ..events import EventBus
from ..ir import ImportStatement, TestModule
from ..pattern_analyzer import UnittestPatternAnalyzer
from ..pipeline import Step
from ..result import Result


class UnittestToIRStep(Step[cst.Module, TestModule]):
    """Convert a ``libcst.Module`` into a :class:`TestModule` IR.

    The step uses :class:`UnittestPatternAnalyzer` to extract test classes,
    methods, assertions, and fixtures, then augments the IR with import
    information discovered in the original module.
    """

    def __init__(self, name: str, event_bus: EventBus):
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, module: cst.Module) -> Result[TestModule]:
        """Run pattern analysis over a parsed CST module and produce IR.

        Args:
            context: Pipeline execution context that may contain source file
                information and configuration used to populate metadata.
            module: A parsed ``libcst.Module`` representing the source file.

        Returns:
            A :class:`Result` containing the populated :class:`TestModule` on
            success or a failure result with the exception on error.
        """
        try:
            # Get the source code from the module
            source_code = module.code

            # Create pattern analyzer
            analyzer = UnittestPatternAnalyzer()

            # Analyze the module
            ir_module = analyzer.analyze_module(source_code)

            # Update module name from context if available
            if hasattr(context, "source_file") and context.source_file:
                ir_module.name = Path(context.source_file).stem

            # Collect import information
            self._analyze_imports(module, ir_module)

            return Result.success(
                ir_module,
                metadata={
                    "classes_found": len(ir_module.classes),
                    "assertions_found": sum(len(cls.methods) for cls in ir_module.classes),
                    "fixtures_found": ir_module.get_fixture_count(),
                    "needs_pytest": ir_module.needs_pytest_import,
                },
            )

        except Exception as e:
            return Result.failure(e)

    def _analyze_imports(self, module: cst.Module, ir_module: TestModule) -> None:
        """Extract import statements from the CST module and add to the IR.

        Args:
            module: ``libcst.Module`` to inspect for import statements.
            ir_module: :class:`TestModule` instance to be updated with
                discovered :class:`ImportStatement` objects.
        """
        for stmt in module.body:
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.Expr):
                        # Skip expressions for now
                        continue

                    # Check for import statements
                    if isinstance(item, cst.Import | cst.ImportFrom):
                        import_stmt = self._parse_import_statement(item)
                        if import_stmt:
                            ir_module.add_import(import_stmt)

    def _parse_import_statement(self, node: Any) -> ImportStatement | None:
        """Parse a CST import node and return an :class:`ImportStatement`.

        Args:
            node: A libcst import node (``Import`` or ``ImportFrom``).

        Returns:
            An :class:`ImportStatement` describing the import, or ``None`` if
            the node cannot be represented.
        """
        if isinstance(node, cst.Import):
            # Direct import: import os, sys
            module_names = []
            for alias in node.names:
                if isinstance(alias.name, cst.Name):
                    module_names.append(alias.name.value)
                    if alias.asname and isinstance(alias.asname.name, cst.Name):
                        # This is an alias: import os as operating_system
                        return ImportStatement(
                            module=str(alias.name.value), imported_items=[], alias=str(alias.asname.name.value)
                        )
                else:
                    # Handle complex name expressions
                    module_names.append(str(alias.name))

            # Regular import without alias
            if len(module_names) == 1:
                return ImportStatement(module=str(module_names[0]))
            else:
                # Multiple imports: import os, sys
                # For now, create separate statements
                return ImportStatement(module=str(module_names[0]))

        elif isinstance(node, cst.ImportFrom):
            # From import: from os import path
            module_name = self._get_importfrom_module(node)

            imported_items = []
            # Handle both ImportAlias and ImportStar cases
            if hasattr(node.names, "__iter__"):
                for alias in node.names:
                    if isinstance(alias.name, cst.Name):
                        imported_items.append(str(alias.name.value))
                        if alias.asname:
                            # Alias: from os import path as os_path
                            return ImportStatement(
                                module=module_name,
                                imported_items=[str(alias.name.value)],
                                alias=str(alias.asname.name.value)
                                if isinstance(alias.asname.name, cst.Name)
                                else str(alias.asname.name),
                                import_type="from",
                            )
                    else:
                        # Handle complex name expressions
                        imported_items.append(str(alias.name))
                        # ImportStar case
                        return ImportStatement(module=module_name, imported_items=["*"], import_type="from")
            else:
                # ImportStar case
                return ImportStatement(module=module_name, imported_items=["*"], import_type="from")

            return ImportStatement(module=module_name, imported_items=imported_items, import_type="from")

        return None

    def _get_importfrom_module(self, node: cst.ImportFrom) -> str:
        """Return the module name string for an ``ImportFrom`` node.

        Args:
            node: libcst ``ImportFrom`` node.

        Returns:
            The module name as a string or an empty string for relative imports
            without an explicit module.
        """
        if node.module:
            return str(node.module.value)
        return ""  # Relative import
