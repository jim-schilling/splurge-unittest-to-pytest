"""Unit tests for decision analysis job and steps.

This module tests the decision analysis job pipeline and its
individual steps for correctness and error handling.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.decision_model import DecisionModel
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.jobs.decision_analysis_job import (
    ClassScannerStep,
    DecisionAnalysisJob,
    FunctionScannerStep,
    ModuleScannerStep,
    ParseSourceForAnalysisStep,
    ProposalReconcilerStep,
)
from splurge_unittest_to_pytest.result import Result


class TestDecisionAnalysisJob:
    """Test DecisionAnalysisJob creation and execution."""

    def test_job_creation(self):
        """Test creating DecisionAnalysisJob."""
        event_bus = EventBus()
        job = DecisionAnalysisJob(event_bus)

        assert job.name == "decision_analysis"
        assert len(job.tasks) == 1
        assert job.tasks[0].name == "analyze_source"

    def test_job_task_structure(self):
        """Test that the job creates the correct task structure."""
        event_bus = EventBus()
        job = DecisionAnalysisJob(event_bus)

        task = job.tasks[0]
        assert len(task.steps) == 5

        # Check step types (by name for now since we can't easily check types)
        step_names = [step.name for step in task.steps]
        expected_names = [
            "parse_for_analysis",
            "module_scanner",
            "class_scanner",
            "function_scanner",
            "proposal_reconciler",
        ]
        assert step_names == expected_names


class TestParseSourceForAnalysisStep:
    """Test ParseSourceForAnalysisStep."""

    def test_parse_valid_source(self):
        """Test parsing valid Python source code."""
        source_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)
"""

        step = ParseSourceForAnalysisStep("test_parse", EventBus())

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            context = PipelineContext.create(source_file=temp_file)
            result = step.execute(context, source_code)

            assert result.is_success()
            assert hasattr(context.metadata, "keys")  # Should have metadata
            assert "cst_module" in context.metadata
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_parse_invalid_source(self):
        """Test parsing invalid Python source code."""
        source_code = "this is not valid python code (("

        step = ParseSourceForAnalysisStep("test_parse", EventBus())

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(source_code)
            temp_file = f.name

        try:
            context = PipelineContext.create(source_file=temp_file)
            result = step.execute(context, source_code)

            assert result.is_error()
        finally:
            Path(temp_file).unlink(missing_ok=True)


class TestModuleScannerStep:
    """Test ModuleScannerStep."""

    def test_module_scanner_execution(self):
        """Test basic module scanner execution."""
        import libcst as cst

        # Create a simple CST module
        module = cst.parse_module("import unittest\n\nclass Test(unittest.TestCase):\n    pass")

        step = ModuleScannerStep("test_module_scan", EventBus())

        # Create a context without file validation for testing
        context = PipelineContext(
            source_file="test.py",
            target_file=None,
            config=MigrationConfig(),
            run_id="test-run",
            metadata={"cst_module": module},
        )

        result = step.execute(context, module)

        assert result.is_success()
        assert "module_proposal" in context.metadata

        proposal = context.metadata["module_proposal"]
        assert proposal.module_name == "test.py"


class TestClassScannerStep:
    """Test ClassScannerStep."""

    def test_class_scanner_execution(self):
        """Test basic class scanner execution."""
        import libcst as cst

        # Create a simple CST module with a class
        module = cst.parse_module("""
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        pass
""")

        step = ClassScannerStep("test_class_scan", EventBus())

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import unittest\nclass Test(unittest.TestCase): pass")
            temp_file = f.name

        try:
            context = PipelineContext.create(source_file=temp_file)
            context.metadata["cst_module"] = module
            context.metadata["module_proposal"] = context.metadata.get("module_proposal")
        finally:
            Path(temp_file).unlink(missing_ok=True)

        result = step.execute(context, module)

        # Should succeed even with basic implementation
        assert result.is_success()

    def test_missing_module_proposal(self):
        """Test class scanner with missing module proposal."""
        import libcst as cst

        module = cst.parse_module("class Test(unittest.TestCase): pass")

        step = ClassScannerStep("test_class_scan", EventBus())

        # Create a context without file validation for testing
        context = PipelineContext(
            source_file="test.py",
            target_file=None,
            config=MigrationConfig(),
            run_id="test-run",
            metadata={"cst_module": module},
        )

        result = step.execute(context, module)

        assert result.is_error()


class TestFunctionScannerStep:
    """Test FunctionScannerStep."""

    def test_function_scanner_execution(self):
        """Test basic function scanner execution."""
        import libcst as cst

        # Create a simple CST module with functions
        module = cst.parse_module("""
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)

    def test_another(self):
        self.assertTrue(True)
""")

        step = FunctionScannerStep("test_function_scan", EventBus())

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import unittest\nclass Test(unittest.TestCase): pass")
            temp_file = f.name

        try:
            context = PipelineContext.create(source_file=temp_file)
            context.metadata["cst_module"] = module
            context.metadata["module_proposal"] = context.metadata.get("module_proposal")
        finally:
            Path(temp_file).unlink(missing_ok=True)

        result = step.execute(context, module)

        # Should succeed even with basic implementation
        assert result.is_success()

    def test_missing_module_proposal(self):
        """Test function scanner with missing module proposal."""
        import libcst as cst

        module = cst.parse_module("def test_func(): pass")

        step = FunctionScannerStep("test_function_scan", EventBus())

        # Create a context without file validation for testing
        context = PipelineContext(
            source_file="test.py",
            target_file=None,
            config=MigrationConfig(),
            run_id="test-run",
            metadata={"cst_module": module},
        )

        result = step.execute(context, module)

        assert result.is_error()


class TestProposalReconcilerStep:
    """Test ProposalReconcilerStep."""

    def test_proposal_reconciler_execution(self):
        """Test basic proposal reconciler execution."""
        import libcst as cst

        module = cst.parse_module("import unittest\n\nclass Test(unittest.TestCase):\n    pass")

        step = ProposalReconcilerStep("test_reconcile", EventBus())

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import unittest\nclass Test(unittest.TestCase): pass")
            temp_file = f.name

        try:
            context = PipelineContext.create(source_file=temp_file)
            context.metadata["cst_module"] = module
            context.metadata["module_proposal"] = context.metadata.get("module_proposal")
        finally:
            Path(temp_file).unlink(missing_ok=True)

        result = step.execute(context, module)

        assert result.is_success()
        decision_model = result.data
        assert isinstance(decision_model, DecisionModel)
        assert len(decision_model.module_proposals) == 1

    def test_missing_module_proposal(self):
        """Test proposal reconciler with missing module proposal."""
        import libcst as cst

        module = cst.parse_module("class Test(unittest.TestCase): pass")

        step = ProposalReconcilerStep("test_reconcile", EventBus())

        # Create a context without file validation for testing
        context = PipelineContext(
            source_file="test.py",
            target_file=None,
            config=MigrationConfig(),
            run_id="test-run",
            metadata={"cst_module": module},
        )

        result = step.execute(context, module)

        assert result.is_error()


class TestIntegration:
    """Integration tests for the complete decision analysis pipeline."""

    def test_end_to_end_analysis(self):
        """Test complete decision analysis pipeline."""
        source_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)
"""

        event_bus = EventBus()
        job = DecisionAnalysisJob(event_bus)

        # Create a context without file validation for testing
        context = PipelineContext(
            source_file="test_example.py", target_file=None, config=MigrationConfig(), run_id="test-run", metadata={}
        )

        result = job.execute(context, source_code)

        # Should succeed and return a DecisionModel
        assert result.is_success()
        decision_model = result.data
        assert isinstance(decision_model, DecisionModel)

        # Should have one module proposal
        assert len(decision_model.module_proposals) == 1
        module_name = list(decision_model.module_proposals.keys())[0]
        assert module_name == "test_example.py"

    def test_analysis_with_config(self):
        """Test decision analysis with configuration."""
        source_code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)
"""

        config = MigrationConfig(enable_decision_analysis=True)
        event_bus = EventBus()
        job = DecisionAnalysisJob(event_bus)

        # Create a context without file validation for testing
        context = PipelineContext(
            source_file="test_example.py", target_file=None, config=config, run_id="test-run", metadata={}
        )

        result = job.execute(context, source_code)

        assert result.is_success()
        decision_model = result.data
        assert isinstance(decision_model, DecisionModel)
