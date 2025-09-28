"""Parsing steps for the migration pipeline.

This module exposes pipeline steps that parse source code into a libcst
``Module``, apply the unittest->pytest transformations at the CST level,
and generate final source code strings for subsequent formatting and output
steps.
"""

import libcst as cst

from ..context import PipelineContext
from ..pipeline import Step
from ..result import Result
from ..transformers import UnittestToPytestCstTransformer


class ParseSourceStep(Step[str, cst.Module]):
    """Parse Python source code into a ``libcst.Module`` for analysis.

    This step uses ``libcst`` to produce a concrete syntax tree for downstream
    transformation and validation steps.
    """

    def execute(self, context: PipelineContext, source_code: str) -> Result[cst.Module]:
        """Parse source code into a ``libcst.Module``.

        Args:
            context: Pipeline execution context (unused by the parser but kept
                for API consistency).
            source_code: Raw Python source text to parse.

        Returns:
            A success :class:`Result` containing the parsed ``libcst.Module``
            or a failure result containing the parsing exception.
        """
        try:
            # Parse the provided source code directly. Test data are expected
            # to be raw Python files and should not require any pre-processing.
            module = cst.parse_module(source_code)
            return Result.success(module)
        except cst.ParserSyntaxError as e:
            return Result.failure(e)


class TransformUnittestStep(Step[cst.Module, cst.Module]):
    """Transform ``unittest.TestCase`` classes to pytest-friendly code.

    The step delegates to :class:`UnittestToPytestCstTransformer` to perform
    assertion rewrites, fixture generation, and other conservative
    transformations on the CST representation.
    """

    def execute(self, context: PipelineContext, module: cst.Module) -> Result[cst.Module]:
        """Apply transformations to convert unittest-style tests to pytest.

        Args:
            context: Pipeline execution context (configuration is used to
                control transformation behavior such as parametrize).
            module: Parsed ``libcst.Module`` to transform.

        Returns:
            A success :class:`Result` containing the transformed
            ``libcst.Module`` or a failure result with the exception.
        """
        try:
            # Use full transform_code to include assertion replacements and imports
            transformer = UnittestToPytestCstTransformer(
                test_prefixes=context.config.test_method_prefixes, parametrize=context.config.parametrize
            )
            source_code: str = module.code
            transformed_code: str = transformer.transform_code(source_code)
            # Parse back into CST for downstream steps
            transformed_module = cst.parse_module(transformed_code)
            return Result.success(transformed_module)
        except Exception as e:
            return Result.failure(e)


class GenerateCodeStep(Step[cst.Module, str]):
    """Generate Python source code from a transformed ``libcst.Module``.

    This step is a thin wrapper around the ``libcst`` module's ``code``
    property and is provided for pipeline consistency.
    """

    def execute(self, context: PipelineContext, module: cst.Module) -> Result[str]:
        """Serialize a transformed CST module to source code.

        Args:
            context: Pipeline execution context (unused but provided for API parity).
            module: Transformed ``libcst.Module`` instance.

        Returns:
            A success :class:`Result` containing the generated source code
            string or a failure result with the exception.
        """
        try:
            generated_code = module.code
            return Result.success(generated_code)
        except Exception as e:
            return Result.failure(e)
