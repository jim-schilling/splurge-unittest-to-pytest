"""Output job for writing generated files to disk.

This job handles the final phase of the pipeline: writing the transformed
and formatted code to disk, creating optional backups, and emitting the
completion events used by callers.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
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
    """Write generated pytest files to the filesystem.

    The job is responsible for creating backups when requested and for
    orchestrating the write to the configured ``context.target_file``.
    """

    def __init__(self, event_bus: EventBus):
        """Initialize the output job.

        Args:
            event_bus: Event bus used for publishing pipeline events.
        """
        super().__init__("output", [self._create_output_task(event_bus)], event_bus)
        self._logger = logging.getLogger(f"{__name__}.{self.name}")

    def _create_output_task(self, event_bus: EventBus) -> Task[Any, Any]:
        """Create and return the output :class:`Task` for this job.

        The task contains the :class:`WriteOutputStep` which performs the
        actual filesystem write (or supplies the code in metadata for dry-run).
        """
        from ..pipeline import Task

        steps: list[Any] = [
            WriteOutputStep("write_output", event_bus),
        ]

        return Task("output", steps, event_bus)

    def execute(self, context: PipelineContext, initial_input: Any = None) -> Result[str]:
        """Run the output job and write the generated file.

        Args:
            context: Pipeline execution context containing ``target_file`` and
                configuration such as backup settings.
            initial_input: The input data passed from the formatting job.

        Returns:
            A :class:`Result` containing the path to the file written (as a
            string) on success or a failure result when the write fails.
        """
        self._logger.info(f"Starting output job for {context.target_file}")

        # Create backup if requested (skip on dry-run)
        if context.config.backup_originals and not context.config.dry_run:
            self._logger.info(f"Creating backup for {context.source_file}")
            self._create_backup(context.source_file, context.config.backup_root)
        else:
            self._logger.debug(
                f"Skipping backup: dry_run={context.config.dry_run}, backup={context.config.backup_originals}"
            )

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

    def _create_backup(self, source_file: str, backup_root: str | None = None) -> None:
        """Create a timestamp-less backup of the original source file.

        When backup_root is specified in the configuration, backups are created
        in that directory while preserving the folder structure relative to the
        source file's location.

        Args:
            source_file: Path to the original file to back up.
            backup_root: Root directory for backup files. If None, backup in same directory as source.
        """
        try:
            source_path = Path(source_file)

            # Determine backup root directory
            if backup_root:
                backup_root_path = Path(backup_root)
                # Preserve folder structure by calculating relative path from source to backup root
                # For now, use the same directory as source if backup_root is specified but no structure preservation
                # In the future, this should be enhanced to work with root_directory for proper structure preservation
                backup_path = backup_root_path / source_path.name
                backup_path = backup_path.with_suffix(f"{source_path.suffix}.backup")
            else:
                # Default behavior: backup in same directory as source
                backup_path = source_path.with_suffix(f"{source_path.suffix}.backup")

            # Ensure backup directory exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Only create backup if it doesn't already exist
            if not backup_path.exists():
                import shutil

                shutil.copy2(source_path, backup_path)
                self._logger.info(f"Created backup: {backup_path}")
            else:
                self._logger.info(f"Backup already exists, skipping: {backup_path}")
        except Exception as e:
            self._logger.warning(f"Failed to create backup for {source_file}: {e}")
