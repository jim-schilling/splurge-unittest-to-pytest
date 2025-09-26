#!/usr/bin/env python3
"""IR Generation Step for converting CST to Intermediate Representation.

This step analyzes unittest code using the pattern analyzer and generates
an IR representation that can be more easily transformed and validated.
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
    """Step that converts CST Module to IR TestModule using pattern analysis."""

    def __init__(self, name: str, event_bus: EventBus):
        super().__init__(name, event_bus)

    def execute(self, context: PipelineContext, module: cst.Module) -> Result[TestModule]:
        """Execute the IR generation step.

        Args:
            context: Pipeline execution context
            module: CST module to analyze

        Returns:
            Result containing the generated TestModule
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
        """Analyze import statements in the module.

        Args:
            module: CST module to analyze
            ir_module: IR module to update with import information
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
        """Parse a CST import node into an IR ImportStatement.

        Args:
            node: CST import node (Import or ImportFrom)

        Returns:
            ImportStatement representing the import
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
        """Get the module name from an ImportFrom node.

        Args:
            node: ImportFrom CST node

        Returns:
            Module name string
        """
        if node.module:
            return str(node.module.value)
        return ""  # Relative import
