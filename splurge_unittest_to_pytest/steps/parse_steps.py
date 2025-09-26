"""Parsing steps for the unittest to pytest migration pipeline."""

import libcst as cst

from ..context import PipelineContext
from ..pipeline import Step
from ..result import Result
from ..transformers import UnittestToPytestTransformer


class ParseSourceStep(Step[str, cst.Module]):
    """Parse Python source code into CST Module."""

    def execute(self, context: PipelineContext, source_code: str) -> Result[cst.Module]:
        """Parse source code using libcst."""
        try:
            module = cst.parse_module(source_code)
            return Result.success(module)
        except cst.ParserSyntaxError as e:
            return Result.failure(e)


class TransformUnittestStep(Step[cst.Module, cst.Module]):
    """Transform unittest.TestCase classes to regular classes with fixtures."""

    def execute(self, context: PipelineContext, module: cst.Module) -> Result[cst.Module]:
        """Apply unittest to pytest transformations."""
        try:
            # Use full transform_code to include assertion replacements and imports
            transformer = UnittestToPytestTransformer(test_prefixes=context.config.test_method_prefixes)
            source_code: str = module.code
            transformed_code: str = transformer.transform_code(source_code)
            # Parse back into CST for downstream steps
            transformed_module = cst.parse_module(transformed_code)
            return Result.success(transformed_module)
        except Exception as e:
            return Result.failure(e)


class GenerateCodeStep(Step[cst.Module, str]):
    """Generate Python source code from CST Module."""

    def execute(self, context: PipelineContext, module: cst.Module) -> Result[str]:
        """Generate code from transformed CST."""
        try:
            generated_code = module.code
            return Result.success(generated_code)
        except Exception as e:
            return Result.failure(e)
