"""Formatter job for applying code formatting and validation.

This job runs code formatting and basic validation steps on generated
source code. It applies ``isort`` for import sorting followed by ``black``
for code formatting and performs a syntax/import validation pass.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
from typing import Any

from ..context import PipelineContext
from ..events import EventBus
from ..pipeline import Job, Task
from ..result import Result
from ..steps import FormatCodeStep, ValidateGeneratedCodeStep


class FormatterJob(Job[str, str]):
    """Format and validate generated pytest code.

    The job wraps formatting steps and provides lifecycle logging for the
    formatting phase.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize the formatter job.

        Args:
            event_bus: Event bus used for publishing pipeline events.
        """
        super().__init__("formatter", [self._create_formatting_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_formatting_task(self, event_bus: EventBus) -> Task[Any, Any]:
        """Create and return the formatting :class:`Task`.

        The formatting task applies formatting and validation steps to the
        input source code.
        """
        from ..pipeline import Task

        steps: list[Any] = [
            FormatCodeStep("format_code", event_bus),
            ValidateGeneratedCodeStep("validate_code", event_bus),
        ]

        return Task("formatting", steps, event_bus)

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[str]:
        """Run the formatter job.

        Args:
            context: Pipeline execution context with configuration and
                target paths.
            initial_input: Source code to format (typically the output of the
                collector job).

        Returns:
            A :class:`Result` containing the formatted source code string on
            success or a failure result when formatting fails.
        """
        self._logger.info(f"Starting formatting job for {context.source_file}")

        # Execute the job, passing along the input from the previous job
        result = super().execute(context, initial_input)

        if result.is_success():
            self._logger.info(f"Formatting job completed successfully for {context.source_file}")
        else:
            self._logger.error(f"Formatting job failed for {context.source_file}: {result.error}")

        return result
