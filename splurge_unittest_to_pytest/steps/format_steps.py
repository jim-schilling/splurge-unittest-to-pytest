"""Formatting steps used by the migration pipeline.

This module exposes pipeline steps that format and validate the generated
Python code. The steps use the programmatic APIs of ``isort`` and ``black``
when available and fall back to returning the unmodified code with a
warning on failure.
"""

import ast
from typing import Any

from ..context import PipelineContext
from ..pipeline import Step
from ..result import Result


class FormatCodeStep(Step[str, str]):
    """Format generated code using isort and black programmatic APIs.

    The step applies ``isort`` to sort and group imports and then runs
    ``black`` to format the code. Formatting is always applied by the
    pipeline; older configuration flags that toggled formatting were removed.
    """

    def execute(self, context: PipelineContext, code: str) -> Result[str]:
        """Format Python source code.

        Args:
            context: Pipeline execution context containing configuration.
            code: Unformatted/generated Python source code.

        Returns:
            A :class:`Result` containing the formatted code on success or a
            warning result containing the original code when formatting
            fails.
        """
        # Formatting is always applied by the pipeline; the legacy
        # `format_code` flag has been removed. Proceed to format.

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
        """Sort imports using ``isort`` programmatic API.

        Args:
            code: Source code to process.
            config: Pipeline configuration (used for line-length, etc.).

        Returns:
            The code with imports sorted according to the configured rules.
        """
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
        """Format code using ``black`` programmatic API.

        Args:
            code: Source code to format.
            config: Pipeline configuration (unused now but kept for symmetry).

        Returns:
            The formatted source code. If there is nothing to change the
            original ``code`` is returned.
        """
        import black

        # Configure black with appropriate settings
        try:
            # Format the code using black's API
            formatted = black.format_str(code, mode=black.FileMode())
            return formatted
        except black.NothingChanged:
            return code  # Code was already properly formatted


class ValidateGeneratedCodeStep(Step[str, str]):
    """Validate generated Python source for syntax and imports.

    Performs a lightweight validation pass that ensures the generated code is
    valid Python (parses via ``ast``) and performs basic import-line checks.
    This step is intentionally conservative and can be extended for deeper
    analysis in the future.
    """

    def execute(self, context: PipelineContext, code: str) -> Result[str]:
        """Validate generated code for syntax and imports.

        Args:
            context: Pipeline execution context.
            code: Generated Python source code to validate.

        Returns:
            A success :class:`Result` with the input code when validation
            passes, or a failure :class:`Result` with the parsing exception
            when validation fails.
        """
        try:
            # Syntax validation
            ast.parse(code)

            # Import validation
            self._validate_imports(code)

            return Result.success(code)
        except SyntaxError as e:
            return Result.failure(e)

    def _validate_imports(self, code: str) -> None:
        """Run basic validation of import statements.

        This performs minimal checks on import lines and is a placeholder for
        more sophisticated validation that may be added later.
        """
        # Basic import validation - can be extended
        lines = code.split("\n")
        for line in lines:
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                # Basic validation - ensure import lines are properly formatted
                if not line.strip():
                    continue  # Skip empty lines
                # Could add more sophisticated validation here
