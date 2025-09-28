"""Output job for writing generated files to disk.

This job handles the final phase of the migration process:
1. Write the transformed and formatted code to the target file
2. Handle backup creation if requested
3. Ensure proper file permissions and encoding
"""

import logging
from pathlib import Path
from typing import Any

from ..context import PipelineContext
from ..events import EventBus
from ..pipeline import Job, Task
from ..result import Result
from ..steps import WriteOutputStep


class OutputJob(Job[str, str]):
    """Job for writing generated pytest files to disk."""

    def __init__(self, event_bus: EventBus):
        """Initialize the output job.

        Args:
            event_bus: Event bus for publishing events
        """
        super().__init__("output", [self._create_output_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_output_task(self, event_bus: EventBus) -> Task[Any, Any]:
        """Create the output task for this job."""
        from ..pipeline import Task

        steps: list[Any] = [
            WriteOutputStep("write_output", event_bus),
        ]

        return Task("output", steps, event_bus)

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[str]:
        """Execute the output job.

        Args:
            context: Pipeline execution context
            initial_input: Input data for the job

        Returns:
            Result containing the path to the file that was written
        """
        self._logger.info(f"Starting output job for {context.target_file}")

        # Create backup if requested (skip on dry-run)
        if context.config.backup_originals and not context.config.dry_run:
            self._create_backup(context.source_file)

        # Execute the job with the transformed code as input
        result = super().execute(context, initial_input)

        if result.is_success():
            if context.config.dry_run:
                self._logger.info(f"Dry-run: would write output to {context.target_file}")
            else:
                self._logger.info(f"Output job completed successfully: {context.target_file}")
        else:
            self._logger.error(f"Output job failed for {context.target_file}: {result.error}")

        return result

    def _create_backup(self, source_file: str) -> None:
        """Create a backup of the original file.

        Args:
            source_file: Path to the source file to backup
        """
        try:
            source_path = Path(source_file)
            backup_path = source_path.with_suffix(f"{source_path.suffix}.backup")

            # Only create backup if it doesn't already exist
            if not backup_path.exists():
                import shutil

                shutil.copy2(source_path, backup_path)
                self._logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            self._logger.warning(f"Failed to create backup for {source_file}: {e}")
