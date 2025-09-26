"""Output steps for the unittest to pytest migration pipeline."""

from pathlib import Path

from ..context import PipelineContext
from ..pipeline import Step
from ..result import Result


class WriteOutputStep(Step[str, str]):
    """Write generated code to target file."""

    def execute(self, context: PipelineContext, code: str) -> Result[str]:
        """Write generated code to target file."""
        if context.config.dry_run:
            return Result.success(code, metadata={"dry_run": True, "target_file": context.target_file})

        try:
            # Ensure target directory exists
            target_path = Path(context.target_file)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            with open(context.target_file, "w", encoding="utf-8") as f:
                f.write(code)
            return Result.success(code)
        except OSError as e:
            return Result.failure(e)
