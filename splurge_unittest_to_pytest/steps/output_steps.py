"""Output steps used by the migration pipeline.

This module contains steps that write generated code to disk or prepare the
generated artifacts for dry-run presentation to callers (for example the CLI).

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

from pathlib import Path

from ..context import PipelineContext
from ..pipeline import Step
from ..result import Result


class WriteOutputStep(Step[str, str]):
    """Write generated code to the configured target file.

    This step either writes the provided source code to ``context.target_file``
    or, when running in dry-run mode, returns the generated code in the
    result metadata so callers can present it without filesystem writes.
    """

    def execute(self, context: PipelineContext, code: str) -> Result[str]:
        """Write the generated code or return it for dry-run.

        Args:
            context: Pipeline execution context with target file and config.
            code: Generated or formatted Python source to write.

        Returns:
            A :class:`Result` with the target file path string on success. In
            dry-run mode the result will include ``generated_code`` in the
            metadata mapping.
        """
        if context.config.dry_run:
            # Include the generated/formatted code in metadata so callers (CLI)
            # can display it for dry-run mode without writing files.
            return Result.success(
                str(context.target_file),
                metadata={
                    "dry_run": True,
                    "target_file": context.target_file,
                    "generated_code": code,
                },
            )

        try:
            # Ensure target directory exists
            target_path = Path(context.target_file)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            with open(context.target_file, "w", encoding="utf-8") as f:
                f.write(code)
            # Return the path of the file we wrote so callers can use it
            return Result.success(str(context.target_file))
        except OSError as e:
            return Result.failure(e)
