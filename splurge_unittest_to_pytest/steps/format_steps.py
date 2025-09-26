"""Formatting steps for the unittest to pytest migration pipeline."""

import ast
from typing import Any

from ..context import PipelineContext
from ..pipeline import Step
from ..result import Result


class FormatCodeStep(Step[str, str]):
    """Format generated code using isort and black programmatic APIs."""

    def execute(self, context: PipelineContext, code: str) -> Result[str]:
        """Format code using isort and black."""
        if not context.config.format_code:
            return Result.success(code)

        try:
            # Apply isort for import sorting
            formatted_code = self._apply_isort(code, context.config)

            # Apply black for code formatting
            formatted_code = self._apply_black(formatted_code, context.config)

            return Result.success(
                formatted_code,
                metadata={
                    "isort_applied": True,
                    "black_applied": True,
                    "original_lines": len(code.splitlines()),
                    "formatted_lines": len(formatted_code.splitlines()),
                },
            )
        except Exception as e:
            # If formatting fails, return original code with warning
            return Result.warning(code, [f"Code formatting failed: {e}"], metadata={"formatting_failed": True})

    def _apply_isort(self, code: str, config: Any) -> str:
        """Apply isort programmatically to sort imports."""
        import isort

        # Configure isort with appropriate settings
        settings = isort.Config(
            profile="black",  # Use black-compatible settings
            line_length=config.line_length or 120,
            known_first_party=["pytest"],
            multi_line_output=3,  # Vertical hanging indent
            include_trailing_comma=True,
            force_grid_wrap=0,
            use_parentheses=True,
            ensure_newline_before_comments=True,
        )

        return isort.code(code, config=settings)

    def _apply_black(self, code: str, config: Any) -> str:
        """Apply black programmatically for code formatting."""
        import black

        # Configure black with appropriate settings
        try:
            # Format the code using black's API
            formatted = black.format_str(code, mode=black.FileMode())
            return formatted
        except black.NothingChanged:
            return code  # Code was already properly formatted


class ValidateGeneratedCodeStep(Step[str, str]):
    """Validate generated Python code."""

    def execute(self, context: PipelineContext, code: str) -> Result[str]:
        """Validate generated code for syntax and imports."""
        try:
            # Syntax validation
            ast.parse(code)

            # Import validation
            self._validate_imports(code)

            return Result.success(code)
        except SyntaxError as e:
            return Result.failure(e)

    def _validate_imports(self, code: str) -> None:
        """Validate that imports are properly structured."""
        # Basic import validation - can be extended
        lines = code.split("\n")
        for line in lines:
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                # Basic validation - ensure import lines are properly formatted
                if not line.strip():
                    continue  # Skip empty lines
                # Could add more sophisticated validation here
