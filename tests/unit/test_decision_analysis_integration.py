"""Integration tests for the complete decision analysis pipeline.

This module tests the end-to-end analysis of real unittest code patterns
to verify that the decision analysis produces correct recommendations.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import tempfile
from pathlib import Path

import libcst as cst
import pytest

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.decision_model import DecisionModel
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.jobs.decision_analysis_job import DecisionAnalysisJob


class TestDecisionAnalysisIntegration:
    """Test complete decision analysis on real code patterns."""

    def test_simple_subtest_loop_analysis(self):
        """Test analysis of a simple subTest loop that should be parametrized."""
        source_code = """
import unittest

class TestCalculator(unittest.TestCase):
    def test_addition_cases(self):
        test_cases = [
            (1, 2, 3),
            (0, 0, 0),
            (-1, 1, 0)
        ]

        for a, b, expected in test_cases:
            with self.subTest(a=a, b=b):
                result = a + b
                self.assertEqual(result, expected)
"""

        decision_model = self._run_analysis(source_code)

        # Should find one function with parametrize recommendation
        assert len(decision_model.module_proposals) == 1
        module_prop = list(decision_model.module_proposals.values())[0]
        assert len(module_prop.class_proposals) == 1

        class_prop = list(module_prop.class_proposals.values())[0]
        assert len(class_prop.function_proposals) == 1

        func_prop = list(class_prop.function_proposals.values())[0]
        assert func_prop.function_name == "TestCalculator.test_addition_cases"
        assert func_prop.recommended_strategy == "parametrize"
        assert func_prop.loop_var_name == "a"  # First variable in the tuple unpacking
        assert "Found name reference" in " ".join(func_prop.evidence)

    def test_accumulator_pattern_analysis(self):
        """Test analysis of accumulator pattern that should use subtests."""
        source_code = """
import unittest

class TestDataProcessor(unittest.TestCase):
    def test_process_scenarios(self):
        scenarios = []

        # Accumulator pattern - scenarios is mutated
        scenarios.append({"input": "test1", "expected": "result1"})
        scenarios.append({"input": "test2", "expected": "result2"})

        for scenario in scenarios:
            with self.subTest(scenario=scenario["input"]):
                result = scenario["input"].upper()
                self.assertEqual(result, scenario["expected"])
"""

        decision_model = self._run_analysis(source_code)

        # Should recommend subtests due to accumulator pattern
        func_prop = self._get_function_proposal(decision_model, "TestDataProcessor.test_process_scenarios")
        assert func_prop.recommended_strategy == "subtests"
        assert "Variable scenarios is mutated" in " ".join(func_prop.evidence)

    def test_range_call_analysis(self):
        """Test analysis of range() call that should be parametrized."""
        source_code = """
import unittest

class TestRange(unittest.TestCase):
    def test_range_cases(self):
        for i in range(5):
            with self.subTest(i=i):
                self.assertGreaterEqual(i, 0)
                self.assertLess(i, 5)
"""

        decision_model = self._run_analysis(source_code)

        # Should recommend parametrize for range() call
        func_prop = self._get_function_proposal(decision_model, "TestRange.test_range_cases")
        assert func_prop.recommended_strategy == "parametrize"
        assert "range() call" in " ".join(func_prop.evidence)

    def test_mixed_strategies_reconciliation(self):
        """Test that mixed strategies maintain individual function decisions."""
        source_code = """
import unittest

class TestMixed(unittest.TestCase):
    def test_literal_cases(self):
        cases = [1, 2, 3]
        for case in cases:
            with self.subTest(case=case):
                self.assertIn(case, [1, 2, 3])

    def test_accumulator_cases(self):
        cases = []
        cases.append(4)
        cases.append(5)
        for case in cases:
            with self.subTest(case=case):
                self.assertIn(case, [4, 5])
"""

        decision_model = self._run_analysis(source_code)

        # Functions should maintain their individual strategies based on their own analysis
        func_prop1 = self._get_function_proposal(decision_model, "TestMixed.test_literal_cases")
        assert func_prop1.recommended_strategy == "parametrize"
        assert "not mutated" in " ".join(func_prop1.evidence)

        func_prop2 = self._get_function_proposal(decision_model, "TestMixed.test_accumulator_cases")
        assert func_prop2.recommended_strategy == "subtests"
        assert "mutated" in " ".join(func_prop2.evidence)

    def test_no_subtest_functions(self):
        """Test analysis of functions without subTest loops."""
        source_code = """
import unittest

class TestSimple(unittest.TestCase):
    def test_simple_case(self):
        self.assertTrue(True)

    def test_another_case(self):
        self.assertEqual(1, 1)
"""

        decision_model = self._run_analysis(source_code)

        # Should find two functions with keep-loop strategy
        func_props = self._get_all_function_proposals(decision_model)
        assert len(func_props) == 2

        for func_prop in func_props.values():
            assert func_prop.recommended_strategy == "keep-loop"
            assert "No subTest loops detected" in func_prop.evidence

    def test_module_level_metadata_collection(self):
        """Test that module-level metadata is collected correctly."""
        source_code = """
import unittest
from pytest import fixture

TEST_DATA = [
    {"input": 1, "expected": 2},
    {"input": 3, "expected": 4}
]

@fixture
def sample_data():
    return "test"

class TestWithMetadata(unittest.TestCase):
    def test_with_data(self):
        for item in TEST_DATA:
            with self.subTest(item=item):
                self.assertEqual(item["input"] * 2, item["expected"])
"""

        decision_model = self._run_analysis(source_code)

        # Check module-level metadata
        module_prop = list(decision_model.module_proposals.values())[0]
        assert len(module_prop.module_imports) >= 2  # Should have unittest and pytest imports
        assert "import unittest" in module_prop.module_imports
        assert "from pytest import fixture" in module_prop.module_imports

        assert "TEST_DATA" in module_prop.top_level_assignments
        assert "List (literal)" in module_prop.top_level_assignments["TEST_DATA"]

        assert "sample_data" in module_prop.module_fixtures

    def _run_analysis(self, source_code: str) -> DecisionModel:
        """Run complete decision analysis on source code."""
        # Create a temporary file for the source
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            # Create context and run analysis
            event_bus = EventBus()
            job = DecisionAnalysisJob(event_bus)

            context = PipelineContext(
                source_file=temp_file, target_file=None, config=MigrationConfig(), run_id="test-run", metadata={}
            )

            result = job.execute(context, source_code)
            assert result.is_success()

            # DecisionModel is now stored in context metadata
            return context.metadata["decision_model"]

        finally:
            Path(temp_file).unlink(missing_ok=True)

    def _get_function_proposal(self, decision_model: DecisionModel, function_name: str):
        """Get a specific function proposal from the decision model."""
        all_funcs = self._get_all_function_proposals(decision_model)
        return all_funcs[function_name]

    def _get_all_function_proposals(self, decision_model: DecisionModel):
        """Get all function proposals from the decision model."""
        all_proposals = {}
        for module_prop in decision_model.module_proposals.values():
            for class_prop in module_prop.class_proposals.values():
                all_proposals.update(class_prop.function_proposals)
        return all_proposals
