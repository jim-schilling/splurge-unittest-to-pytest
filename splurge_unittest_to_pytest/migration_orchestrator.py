"""Main migration orchestrator that coordinates all jobs.

This module provides the high-level orchestration of the entire
migration process, coordinating the collector, transformer, formatter,
and output jobs.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import logging
from pathlib import Path
from typing import Any

from .context import MigrationConfig, PipelineContext
from .events import EventBus, LoggingSubscriber
from .jobs import CollectorJob, FormatterJob, OutputJob
from .jobs.decision_analysis_job import DecisionAnalysisJob
from .pipeline import Pipeline
from .result import Result


class MigrationOrchestrator:
    """Main orchestrator for unittest-to-pytest migration.

    The orchestrator wires together jobs and pipelines, exposes file and
    directory migration helpers, and publishes lifecycle events on the
    internal event bus.
    """

    def __init__(self) -> None:
        """Initialize the migration orchestrator."""
        self.event_bus = EventBus()
        self.logger_subscriber = LoggingSubscriber(self.event_bus)
        self._logger = logging.getLogger(__name__)

        # Create job instances
        self.collector_job = CollectorJob(self.event_bus)
        self.formatter_job = FormatterJob(self.event_bus)
        self.output_job = OutputJob(self.event_bus)
        self.decision_analysis_job = DecisionAnalysisJob(self.event_bus)

        self._logger.info("Migration orchestrator initialized")

    def migrate_file(self, source_file: str, config: MigrationConfig | None = None) -> Result[str]:
        """Migrate a single unittest file to pytest.

        Args:
            source_file: Path to the source unittest file.
            config: Optional ``MigrationConfig`` to control behavior.

        Returns:
            ``Result`` containing the path to the migrated file on
            success, or a failure ``Result`` with diagnostic details.
        """
        if config is None:
            config = MigrationConfig()

        self._logger.info(f"Starting migration of {source_file}")

        # Validate source file exists
        if not Path(source_file).exists():
            return Result.failure(FileNotFoundError(f"Source file not found: {source_file}"))

        # Determine target file path. If a target_directory is provided in
        # the config, use it while preserving the original filename and
        # extension. Otherwise, let PipelineContext.create compute a default
        # (which preserves the original extension unless overridden by
        # `target_extension`/`target_suffix`).
        target_file: str | None = None
        suffix = config.target_suffix if config else ""

        if config and config.target_directory:
            src_path = Path(source_file)
            dest_dir = Path(config.target_directory)
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Determine extension to use (override if provided)
            ext_to_use = config.target_extension if config.target_extension is not None else src_path.suffix
            if suffix:
                # Append suffix to the stem, preserve/override extension
                new_name = f"{src_path.stem}{suffix}{ext_to_use}"
            else:
                # No suffix: preserve full stem and set extension (may be same as original)
                new_name = f"{src_path.stem}{ext_to_use}"

            target_file = str(dest_dir.joinpath(new_name))
        else:
            # No explicit target_directory; if a suffix is provided, apply
            # it to the filename stem. We construct a tentative target and
            # pass it in; otherwise leave target_file as None to let
            # PipelineContext.create decide (which will preserve the
            # original extension by default).
            if suffix:
                src_path = Path(source_file)
                # keep original extension (unless target_extension provided),
                # but add suffix to stem.
                ext_to_use = config.target_extension if config.target_extension is not None else src_path.suffix
                tentative = f"{src_path.stem}{suffix}{ext_to_use}"
                # Create target path alongside the source
                target_file = str(src_path.with_name(tentative))

        # Create pipeline context
        context = PipelineContext.create(source_file=source_file, target_file=target_file, config=config)

        # Create the main migration pipeline
        pipeline = self._create_migration_pipeline(config)

        # Read source file content for initial input
        try:
            with open(source_file, encoding="utf-8") as f:
                source_code = f.read()
            self._logger.debug(f"Read source code: {len(source_code)} characters")
        except Exception as e:
            return Result.failure(e)

        # Execute the pipeline with source code as initial input
        result = pipeline.execute(context, source_code)
        if result.is_success():
            self._logger.info(f"Migration completed successfully for {source_file}")
            # If running in dry-run, run a preview pipeline (collector +
            # formatter) to produce the transformed and formatted code so it
            # can be printed to stdout. This avoids relying on the final
            # pipeline metadata propagation which may vary across steps.
            if config.dry_run:
                try:
                    preview_jobs: list[Any] = [self.collector_job, self.formatter_job]
                    preview_pipeline: Pipeline[str, str] = Pipeline("dryrun_preview", preview_jobs, self.event_bus)
                    preview_result = preview_pipeline.execute(context, source_code)
                    if preview_result.is_success():
                        gen_code = preview_result.data
                        # Return a success Result that includes the generated
                        # code in metadata so callers (CLI) can access and
                        # print it. Ensure we return a str for the primary data
                        # (path) to satisfy Result[str].
                        primary = getattr(result, "data", "")
                        primary_str = primary if isinstance(primary, str) else str(primary)
                        return Result.success(primary_str, metadata={"generated_code": gen_code})
                except Exception:
                    # Fall back to returning the original result
                    pass
        else:
            self._logger.error(f"Migration failed for {source_file}: {result.error}")

        return result

    def migrate_directory(self, source_dir: str, config: MigrationConfig | None = None) -> Result[list[str]]:
        """Migrate all unittest files under a directory.

        Args:
            source_dir: Path to the source directory.
            config: Optional ``MigrationConfig`` to control behavior.

        Returns:
            ``Result`` containing a list of migrated file paths on
            success. On partial failures a ``warning`` result is
            returned with metadata listing failed files.
        """
        if config is None:
            config = MigrationConfig()

        source_path = Path(source_dir)
        if not source_path.exists():
            return Result.failure(FileNotFoundError(f"Source directory not found: {source_dir}"))

        if not source_path.is_dir():
            return Result.failure(ValueError(f"Path is not a directory: {source_dir}"))

        self._logger.info(f"Starting migration of directory {source_dir}")

        # Find all Python files
        python_files = list(source_path.rglob("*.py"))
        if not python_files:
            self._logger.warning(f"No Python files found in {source_dir}")
            return Result.success([])

        # Filter for unittest files (basic heuristic)
        unittest_files = []
        for py_file in python_files:
            if self._is_unittest_file(py_file):
                unittest_files.append(str(py_file))

        if not unittest_files:
            self._logger.warning(f"No unittest files found in {source_dir}")
            return Result.success([])

        self._logger.info(f"Found {len(unittest_files)} unittest files to migrate")

        # Migrate each file
        successful_migrations = []
        failed_migrations = []

        for unittest_file in unittest_files:
            result = self.migrate_file(unittest_file, config)

            if result.is_success():
                successful_migrations.append(unittest_file)
            else:
                failed_migrations.append(unittest_file)
                self._logger.error(f"Failed to migrate {unittest_file}: {result.error}")

        self._logger.info(
            f"Migration completed: {len(successful_migrations)} successful, {len(failed_migrations)} failed"
        )

        if failed_migrations:
            return Result.warning(
                successful_migrations,
                [f"Failed to migrate {len(failed_migrations)} files"],
                metadata={"failed_files": failed_migrations},
            )

        return Result.success(successful_migrations)

    def _create_migration_pipeline(self, config: MigrationConfig | None = None) -> Pipeline[str, str]:
        """Create the main migration pipeline.

        Args:
            config: Optional migration configuration to control pipeline composition.

        Returns:
            Configured migration ``Pipeline`` instance.
        """
        # Build a pipeline that runs decision analysis -> collector -> formatter -> output
        # Decision analysis is now always enabled for improved transformation accuracy
        # DecisionAnalysisJob: str -> str (analyzes source and stores DecisionModel in context)
        # CollectorJob: str -> str (transforms using DecisionModel from context)
        jobs: list[Any] = [self.decision_analysis_job, self.collector_job, self.formatter_job, self.output_job]

        return Pipeline("migration", jobs, self.event_bus)

    def _is_unittest_file(self, file_path: Path) -> bool:
        """Check heuristically whether a Python file contains unittest code.

        Args:
            file_path: Path to the Python file.

        Returns:
            ``True`` if the file likely contains ``unittest`` patterns,
            otherwise ``False``.
        """
        try:
            content = file_path.read_text(encoding="utf-8")

            # Look for common unittest patterns
            unittest_indicators = [
                "import unittest",
                "from unittest import",
                "unittest.TestCase",
                "self.assertEqual",
                "self.assertTrue",
                "self.assertFalse",
            ]

            return any(indicator in content for indicator in unittest_indicators)
        except Exception:
            # If we can't read the file, assume it's not a unittest file
            return False
