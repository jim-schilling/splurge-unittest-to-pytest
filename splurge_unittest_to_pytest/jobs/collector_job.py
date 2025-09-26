"""Collector job for parsing and analyzing unittest files.

This job handles the initial phase of the migration process:
1. Parse Python source code into CST
2. Analyze the code structure
3. Extract metadata about the test files
4. Prepare for transformation phase
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
    """Job for collecting and parsing unittest source files."""

    def __init__(self, event_bus: EventBus):
        """Initialize the collector job.

        Args:
            event_bus: Event bus for publishing events
        """
        super().__init__("collector", [self._create_parsing_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_parsing_task(self, event_bus: EventBus) -> Task[Any, Any]:
        """Create the parsing task for this job."""
        from ..pipeline import Task

        steps: list[Any] = [
            ParseSourceStep("parse_source", event_bus),
            TransformUnittestStep("transform_unittest", event_bus),
            GenerateCodeStep("generate_code", event_bus),
        ]

        return Task("parsing", steps, event_bus)

    def execute(self, context: PipelineContext) -> Result[str]:
        """Execute the collector job.

        Args:
            context: Pipeline execution context

        Returns:
            Result containing the processed source code
        """
        self._logger.info(f"Starting collection job for {context.source_file}")

        # Validate source file exists
        if not Path(context.source_file).exists():
            return Result.failure(FileNotFoundError(f"Source file not found: {context.source_file}"))

        # Execute the job using the source file as input
        result = super().execute(context)

        if result.is_success():
            self._logger.info(f"Collection job completed successfully for {context.source_file}")
        else:
            self._logger.error(f"Collection job failed for {context.source_file}: {result.error}")

        return result
