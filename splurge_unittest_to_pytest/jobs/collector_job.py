"""Collector job for parsing and analyzing unittest source files.

This job performs the initial phases of the migration pipeline:

- Parse the Python source into a ``libcst`` module
- Analyze the code structure and extract test metadata using the pattern
    analyzer
- Prepare transformed code for subsequent formatting and output steps
"""

import logging
from pathlib import Path
from typing import Any

from ..context import PipelineContext
from ..events import EventBus
from ..pipeline import Job, Task
from ..result import Result
from ..steps import GenerateCodeStep, ParseSourceStep, TransformUnittestStep


class CollectorJob(Job[str, str]):
    """Collect and parse unittest source files into generated code.

    The job coordinates parsing, transformation, and code generation steps and
    emits lifecycle events via the provided :class:`EventBus`.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize the collector job.

        Args:
            event_bus: Event bus used for publishing pipeline events.
        """
        super().__init__("collector", [self._create_parsing_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_parsing_task(self, event_bus: EventBus) -> Task[str, str]:
        """Create and return the parsing :class:`Task` for this job.

        The parsing task includes steps for parsing, transforming, and
        generating source code from the CST.
        """
        from ..pipeline import Task

        steps: list[Any] = [
            ParseSourceStep("parse_source", event_bus),
            TransformUnittestStep("transform_unittest", event_bus),
            GenerateCodeStep("generate_code", event_bus),
        ]

        return Task("parsing", steps, event_bus)

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[str]:
        """Run the collector job.

        Args:
            context: Pipeline execution context containing the source file
                path and configuration.
            initial_input: Optional initial input passed from a previous job.

        Returns:
            A :class:`Result` containing the generated source code
            (string) on success or a failure result with the exception.
        """
        self._logger.info(f"Starting collection job for {context.source_file}")

        # Validate source file exists
        if not Path(context.source_file).exists():
            return Result.failure(FileNotFoundError(f"Source file not found: {context.source_file}"))

        # Execute the job using the source file as input
        result = super().execute(context, initial_input)

        if result.is_success():
            self._logger.info(f"Collection job completed successfully for {context.source_file}")
        else:
            self._logger.error(f"Collection job failed for {context.source_file}: {result.error}")

        return result
