"""Formatter job for applying code formatting and validation.

This job handles the formatting phase of the migration process:
1. Apply isort for import sorting
2. Apply black for code formatting
3. Validate the generated code
"""

import logging
from typing import Any

from ..context import PipelineContext
from ..events import EventBus
from ..pipeline import Job, Task
from ..result import Result
from ..steps import FormatCodeStep, ValidateGeneratedCodeStep


class FormatterJob(Job[str, str]):
    """Job for formatting and validating generated pytest code."""

    def __init__(self, event_bus: EventBus):
        """Initialize the formatter job.

        Args:
            event_bus: Event bus for publishing events
        """
        super().__init__("formatter", [self._create_formatting_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_formatting_task(self, event_bus: EventBus) -> Task[Any, Any]:
        """Create the formatting task for this job."""
        from ..pipeline import Task

        steps: list[Any] = [
            FormatCodeStep("format_code", event_bus),
            ValidateGeneratedCodeStep("validate_code", event_bus),
        ]

        return Task("formatting", steps, event_bus)

    def execute(self, context: PipelineContext) -> Result[str]:
        """Execute the formatter job.

        Args:
            context: Pipeline execution context
            source_code: Source code to format

        Returns:
            Result containing the formatted source code
        """
        self._logger.info(f"Starting formatting job for {context.source_file}")

        # Execute the job
        result = super().execute(context)

        if result.is_success():
            self._logger.info(f"Formatting job completed successfully for {context.source_file}")
        else:
            self._logger.error(f"Formatting job failed for {context.source_file}: {result.error}")

        return result
