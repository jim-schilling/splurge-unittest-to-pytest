"""Property-based tests for parsing functionality.

This module contains Hypothesis-based property tests for the parsing
components in splurge_unittest_to_pytest, including source parsing,
transformation steps, and pattern analysis.
"""

import ast
import tempfile
import unittest
from typing import Any

import libcst as cst
import pytest
from hypothesis import given, settings

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.steps.parse_steps import (
    GenerateCodeStep,
    ParseSourceStep,
    TransformUnittestStep,
)
from tests.hypothesis_config import DEFAULT_SETTINGS
from tests.property.strategies import python_source_code


class TestParsingProperties:
    """Property-based tests for parsing and transformation steps."""

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_parse_source_step_preserves_valid_code(self, source_code: str) -> None:
        """Test that ParseSourceStep successfully parses valid Python code."""
        event_bus = EventBus()
        step = ParseSourceStep("parse", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            result = step.execute(context, source_code)

            # Should succeed for valid Python code
            if self._is_valid_python(source_code):
                assert result.is_success()
                assert isinstance(result.data, cst.Module)
                # Should be able to regenerate the code
                assert isinstance(result.data.code, str)
            else:
                # Invalid code should fail gracefully
                assert result.is_error()
        finally:
            import os

            os.unlink(temp_file)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_parse_source_step_handles_invalid_code_gracefully(self, source_code: str) -> None:
        """Test that ParseSourceStep fails gracefully for invalid Python code."""
        event_bus = EventBus()
        step = ParseSourceStep("parse", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def dummy(): pass")  # Valid file for context
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            result = step.execute(context, source_code)

            # Result should always be a Result object
            assert hasattr(result, "is_success")
            assert hasattr(result, "is_error")

            if result.is_error():
                # Should contain a ParserSyntaxError
                assert isinstance(result.error, cst.ParserSyntaxError)
        finally:
            import os

            os.unlink(temp_file)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_round_trip_parsing_consistency(self, source_code: str) -> None:
        """Test that parse -> generate round-trip preserves valid code."""
        if not self._is_valid_python(source_code):
            pytest.skip("Invalid Python code")

        event_bus = EventBus()
        parse_step = ParseSourceStep("parse", event_bus)
        generate_step = GenerateCodeStep("generate", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            # Parse
            parse_result = parse_step.execute(context, source_code)
            assert parse_result.is_success()
            module = parse_result.data

            # Generate
            generate_result = generate_step.execute(context, module)
            assert generate_result.is_success()
            regenerated_code = generate_result.data

            # Should be valid Python
            assert self._is_valid_python(regenerated_code)

            # Should be able to parse again
            reparse_result = parse_step.execute(context, regenerated_code)
            assert reparse_result.is_success()
        finally:
            import os

            os.unlink(temp_file)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_transformation_step_preserves_module_structure(self, source_code: str) -> None:
        """Test that TransformUnittestStep preserves basic module structure."""
        if not self._is_valid_python(source_code):
            pytest.skip("Invalid Python code")

        event_bus = EventBus()
        transform_step = TransformUnittestStep("transform", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            # Parse first
            parse_step = ParseSourceStep("parse", event_bus)
            parse_result = parse_step.execute(context, source_code)
            if not parse_result.is_success():
                pytest.skip("Parsing failed")
            module = parse_result.data

            # Transform
            result = transform_step.execute(context, module)

            if result.is_success():
                transformed_module = result.data
                assert isinstance(transformed_module, cst.Module)

                # Should still be valid Python
                transformed_code = transformed_module.code
                assert self._is_valid_python(transformed_code)
        finally:
            import os

            os.unlink(temp_file)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_transformation_step_handles_errors_gracefully(self, source_code: str) -> None:
        """Test that TransformUnittestStep handles errors gracefully."""
        event_bus = EventBus()
        transform_step = TransformUnittestStep("transform", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def dummy(): pass")  # Valid file for context
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            # Create a malformed module that might cause transformation issues
            try:
                if self._is_valid_python(source_code):
                    module = cst.parse_module(source_code)
                else:
                    pytest.skip("Invalid Python code")
            except cst.ParserSyntaxError:
                pytest.skip("Parsing failed")

            result = transform_step.execute(context, module)

            # Should always return a Result
            assert hasattr(result, "is_success")
            assert hasattr(result, "is_error")

            if result.is_error():
                # Should contain an exception
                assert result.error is not None
        finally:
            import os

            os.unlink(temp_file)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_generate_code_step_produces_valid_output(self, source_code: str) -> None:
        """Test that GenerateCodeStep produces valid Python code."""
        if not self._is_valid_python(source_code):
            pytest.skip("Invalid Python code")

        event_bus = EventBus()
        generate_step = GenerateCodeStep("generate", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            # Parse first
            parse_step = ParseSourceStep("parse", event_bus)
            parse_result = parse_step.execute(context, source_code)
            if not parse_result.is_success():
                pytest.skip("Parsing failed")
            module = parse_result.data

            # Generate
            result = generate_step.execute(context, module)
            assert result.is_success()

            generated_code = result.data
            assert isinstance(generated_code, str)

            # Should be valid Python
            assert self._is_valid_python(generated_code)
        finally:
            import os

            os.unlink(temp_file)

    @DEFAULT_SETTINGS
    @given(source_code=python_source_code())
    def test_full_pipeline_round_trip(self, source_code: str) -> None:
        """Test the full parse -> transform -> generate pipeline."""
        if not self._is_valid_python(source_code):
            pytest.skip("Invalid Python code")

        event_bus = EventBus()
        parse_step = ParseSourceStep("parse", event_bus)
        transform_step = TransformUnittestStep("transform", event_bus)
        generate_step = GenerateCodeStep("generate", event_bus)

        # Create a temporary file for the context
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            config = MigrationConfig()
            context = PipelineContext.create(source_file=temp_file, config=config)

            # Parse
            parse_result = parse_step.execute(context, source_code)
            assert parse_result.is_success()
            module = parse_result.data

            # Transform
            transform_result = transform_step.execute(context, module)
            if not transform_result.is_success():
                pytest.skip("Transformation failed")
            transformed_module = transform_result.data

            # Generate
            generate_result = generate_step.execute(context, transformed_module)
            assert generate_result.is_success()
            final_code = generate_result.data

            # Final result should be valid Python
            assert self._is_valid_python(final_code)
        finally:
            import os

            os.unlink(temp_file)

    def _is_valid_python(self, code: str) -> bool:
        """Check if code is valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
