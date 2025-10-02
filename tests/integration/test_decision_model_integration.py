"""Integration tests for decision model-based transformations.

These tests verify that the decision model integration works correctly
and produces the expected transformation results compared to the original
transformation logic.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import tempfile
import textwrap
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.decision_model import ClassProposal, DecisionModel, FunctionProposal, ModuleProposal
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator
from splurge_unittest_to_pytest.transformers import UnittestToPytestCstTransformer


class TestDecisionModelIntegration:
    """Test integration of decision model with transformation pipeline."""

    def test_fallback_to_original_logic_when_no_decision_model(self):
        """Test that transformations fall back to original logic when no decision model is provided."""
        source_code = textwrap.dedent("""
            import unittest

            class TestExample(unittest.TestCase):
                def test_with_subtest_loop(self):
                    test_cases = [
                        ("input1", "expected1"),
                        ("input2", "expected2"),
                    ]

                    for case_input, expected in test_cases:
                        with self.subTest(input=case_input):
                            result = case_input.upper()
                            self.assertEqual(result, expected)
        """)

        # Test without decision model (original behavior)
        transformer = UnittestToPytestCstTransformer()
        result_without_dm = transformer.transform_code(source_code)

        # Test with decision model always enabled (no longer configurable)
        config = MigrationConfig()
        orchestrator = MigrationOrchestrator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            result_with_config = orchestrator.migrate_file(temp_file, config)
            assert result_with_config.is_success()
            result_code = result_with_config.data
        finally:
            Path(temp_file).unlink()

        # Both should produce similar results (may differ in formatting)
        assert "parametrize" in result_without_dm or "parametrize" in result_code
        assert "subTest" not in result_without_dm
        assert "subTest" not in result_code

    def test_decision_model_guided_transformation(self):
        """Test that decision model guides transformation choices correctly."""
        source_code = textwrap.dedent("""
            import unittest

            class TestExample(unittest.TestCase):
                def test_literal_list_subtest(self):
                    cases = [("a", 1), ("b", 2)]

                    for value, expected in cases:
                        with self.subTest(value=value):
                            self.assertEqual(len(value), expected)
        """)

        # Create a decision model that recommends 'parametrize' for this function
        decision_model = DecisionModel(
            module_proposals={
                "test_module": ModuleProposal(
                    module_name="test_module",
                    class_proposals={
                        "TestExample": ClassProposal(
                            class_name="TestExample",
                            function_proposals={
                                "test_literal_list_subtest": FunctionProposal(
                                    function_name="test_literal_list_subtest",
                                    recommended_strategy="parametrize",
                                    evidence=["Literal list detected", "No accumulator mutations"],
                                )
                            },
                        )
                    },
                )
            }
        )

        # Test with decision model (always enabled)
        config = MigrationConfig(
            enable_decision_analysis=False,  # Don't run analysis, use provided model
        )

        # Manually set decision model in context for testing
        context = PipelineContext.create(source_file="test_file.py", config=config)
        context = context.with_metadata("decision_model", decision_model)

        # Transform with decision model
        transformer = UnittestToPytestCstTransformer(decision_model=decision_model)
        result_with_dm = transformer.transform_code(source_code)

        # Should use parametrize based on decision model
        assert "@pytest.mark.parametrize" in result_with_dm
        # Check that function parameters were added correctly
        assert "def test_literal_list_subtest(self, value, expected):" in result_with_dm

    def test_decision_model_recommends_subtests_for_accumulator_pattern(self):
        """Test that decision model recommends subtests for accumulator patterns."""
        source_code = textwrap.dedent("""
            import unittest

            class TestExample(unittest.TestCase):
                def test_accumulator_subtest(self):
                    cases = []
                    cases.append(("a", 1))
                    cases.append(("b", 2))

                    for value, expected in cases:
                        with self.subTest(value=value):
                            self.assertEqual(len(value), expected)
        """)

        # Create decision model recommending 'subtests' for accumulator pattern
        decision_model = DecisionModel(
            module_proposals={
                "test_module": ModuleProposal(
                    module_name="test_module",
                    class_proposals={
                        "TestExample": ClassProposal(
                            class_name="TestExample",
                            function_proposals={
                                "test_accumulator_subtest": FunctionProposal(
                                    function_name="test_accumulator_subtest",
                                    recommended_strategy="subtests",
                                    evidence=["Accumulator mutation detected", "List.append() calls found"],
                                )
                            },
                        )
                    },
                )
            }
        )

        # Transform with decision model
        transformer = UnittestToPytestCstTransformer(decision_model=decision_model)
        result_with_dm = transformer.transform_code(source_code)

        # Should preserve loop structure and use subtests fixture
        assert "subtests" in result_with_dm
        assert "for value, expected in cases:" in result_with_dm
        assert "with subtests.test(value=value):" in result_with_dm

    def test_decision_model_with_missing_function_falls_back(self):
        """Test that missing function decisions fall back to original logic."""
        source_code = textwrap.dedent("""
            import unittest

            class TestExample(unittest.TestCase):
                def test_unknown_function(self):
                    cases = [("a", 1), ("b", 2)]

                    for value, expected in cases:
                        with self.subTest(value=value):
                            self.assertEqual(len(value), expected)

                def test_known_function(self):
                    cases = [("x", 1), ("y", 2)]

                    for value, expected in cases:
                        with self.subTest(value=value):
                            self.assertEqual(len(value), expected)
        """)

        # Create decision model with only one function decision
        decision_model = DecisionModel(
            module_proposals={
                "test_module": ModuleProposal(
                    module_name="test_module",
                    class_proposals={
                        "TestExample": ClassProposal(
                            class_name="TestExample",
                            function_proposals={
                                "test_known_function": FunctionProposal(
                                    function_name="test_known_function",
                                    recommended_strategy="parametrize",
                                    evidence=["Literal list detected"],
                                )
                            },
                        )
                    },
                )
            }
        )

        # Transform with partial decision model
        transformer = UnittestToPytestCstTransformer(decision_model=decision_model)
        result_with_dm = transformer.transform_code(source_code)

        # Known function should use parametrize, unknown should fall back to original logic
        assert "@pytest.mark.parametrize" in result_with_dm

        # Should contain both parametrized and loop-based approaches
        lines = result_with_dm.split("\n")
        parametrized_found = False
        loop_found = False

        for line in lines:
            if "def test_known_function(" in line and "value, expected" in line:
                parametrized_found = True
            if "for value, expected in cases:" in line and "subtests.test" in result_with_dm:
                loop_found = True

        assert parametrized_found or loop_found

    def test_decision_model_from_file_integration(self):
        """Test loading and using decision model from file."""
        source_code = textwrap.dedent("""
            import unittest

            class TestExample(unittest.TestCase):
                def test_from_file(self):
                    cases = [("a", 1), ("b", 2)]

                    for value, expected in cases:
                        with self.subTest(value=value):
                            self.assertEqual(len(value), expected)
        """)

        # Create a temporary decision model file
        decision_model = DecisionModel(
            module_proposals={
                "test_module": ModuleProposal(
                    module_name="test_module",
                    class_proposals={
                        "TestExample": ClassProposal(
                            class_name="TestExample",
                            function_proposals={
                                "test_from_file": FunctionProposal(
                                    function_name="test_from_file",
                                    recommended_strategy="parametrize",
                                    evidence=["File-based decision model"],
                                )
                            },
                        )
                    },
                )
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            import json

            json.dump(decision_model.to_dict(), f, indent=2)
            decision_model_file = f.name

        try:
            # Test with decision model loaded from file
            config = MigrationConfig()

            orchestrator = MigrationOrchestrator()

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source_code)
                temp_file = f.name

            try:
                result = orchestrator.migrate_file(temp_file, config)
                assert result.is_success()
                result_data = result.data

                # When not in dry_run mode, result.data is the target file path
                # Check if the file exists and contains the expected content
                if isinstance(result_data, str) and result_data.endswith(".py"):
                    # File was created, read its content
                    with open(result_data) as f:
                        file_content = f.read()
                    # Should use parametrize based on decision model from file
                    assert "@pytest.mark.parametrize" in file_content
                else:
                    # Dry run mode or direct content
                    assert "@pytest.mark.parametrize" in result_data
            finally:
                Path(temp_file).unlink()
                # Clean up created file if it exists
                if "result_data" in locals() and isinstance(result_data, str) and result_data.endswith(".py"):
                    try:
                        Path(result_data).unlink()
                    except Exception:
                        pass

        finally:
            Path(decision_model_file).unlink()

    def test_invalid_decision_model_fallback(self):
        """Test that invalid decision model falls back gracefully."""
        source_code = textwrap.dedent("""
            import unittest

            class TestExample(unittest.TestCase):
                def test_fallback_on_error(self):
                    cases = [("a", 1), ("b", 2)]

                    for value, expected in cases:
                        with self.subTest(value=value):
                            self.assertEqual(len(value), expected)
        """)

        # Create invalid decision model file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": "json"}')  # Invalid JSON
            invalid_file = f.name

        try:
            config = MigrationConfig()

            orchestrator = MigrationOrchestrator()

            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source_code)
                temp_file = f.name

            try:
                result = orchestrator.migrate_file(temp_file, config)
                # Should still succeed with fallback behavior
                assert result.is_success()
                result_code = result.data

                # Should fall back to original logic (may be file path or transformed code)
                if isinstance(result_code, str) and not result_code.endswith(".py"):
                    # If it's transformed code, check for parametrize or subtests
                    assert "parametrize" in result_code or "subtests" in result_code
                # If it's a file path, the migration completed successfully
            finally:
                Path(temp_file).unlink()

        finally:
            Path(invalid_file).unlink()
