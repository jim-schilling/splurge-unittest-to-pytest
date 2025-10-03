"""Unit tests for decision analysis job and steps.

This module tests the decision analysis job pipeline and its
individual steps for correctness and error handling.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.circuit_breaker import CircuitBreakerOpenException
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

    def test_job_execution_error_handling(self, mocker):
        """Test job handles errors properly during execution."""
        event_bus = EventBus()
        job = DecisionAnalysisJob(event_bus)

        # Mock the task execution to raise an exception
        mock_task = mocker.Mock()
        mock_task.execute.side_effect = Exception("Test error")
        job.tasks = [mock_task]

        # Create a basic context
        config = MigrationConfig()
        context = PipelineContext.create("test.py", "test_out.py", config)

        # Execute job - should propagate the error from the task
        # Since we now use circuit breakers, the exception might be wrapped
        with pytest.raises((Exception, CircuitBreakerOpenException), match="Test error"):
            job.execute(context, "invalid source")


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

    def test_module_scanner_error_handling(self, mocker):
        """Test module scanner handles errors properly."""
        import libcst as cst

        # Create a step
        step = ModuleScannerStep("test_module_scan", EventBus())

        # Create a context
        context = PipelineContext(
            source_file="test.py",
            target_file=None,
            config=MigrationConfig(),
            run_id="test-run",
            metadata={},
        )

        # Mock the _collect_imports method to raise an exception
        mocker.patch.object(step, "_collect_imports", side_effect=Exception("Test error"))

        # Create a simple CST module
        module = cst.parse_module("import unittest")

        result = step.execute(context, module)

        # Should return a failure result
        assert not result.is_success()
        assert "Failed to scan module" in str(result.error)


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
        returned_code = result.data
        assert isinstance(returned_code, str)

        # DecisionModel should be stored in context metadata
        decision_model = context.metadata.get("decision_model")
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

        # Should succeed and return the source code (string)
        assert result.is_success()
        returned_code = result.data
        assert isinstance(returned_code, str)

        # DecisionModel should be stored in context metadata
        decision_model = context.metadata.get("decision_model")
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
        returned_code = result.data
        assert isinstance(returned_code, str)

        # DecisionModel should be stored in context metadata
        decision_model = context.metadata.get("decision_model")
        assert isinstance(decision_model, DecisionModel)


class TestDecisionAnalysisJobErrorConditions:
    """Test error condition handling in decision analysis job components."""

    def test_module_scanner_import_collection_error(self, mocker):
        """Test ModuleScannerStep handles _collect_imports errors properly."""
        import libcst as cst

        from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
        from splurge_unittest_to_pytest.jobs.decision_analysis_job import ModuleScannerStep

        step = ModuleScannerStep("test_scanner", mocker.Mock())
        context = PipelineContext.create("test.py", None, MigrationConfig())

        module = cst.parse_module("import unittest\nclass Test(unittest.TestCase): pass")

        # Mock _collect_imports to raise an exception (covers lines 172-173)
        mocker.patch.object(step, "_collect_imports", side_effect=RuntimeError("Import collection failed"))

        result = step.execute(context, module)
        # Should return error result when scanning fails
        assert result.is_error()
        assert "Failed to scan module" in str(result.error)

    def test_module_scanner_assignment_collection_error(self, mocker):
        """Test ModuleScannerStep handles _collect_top_level_assignments errors."""
        import libcst as cst

        from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
        from splurge_unittest_to_pytest.jobs.decision_analysis_job import ModuleScannerStep

        step = ModuleScannerStep("test_scanner", mocker.Mock())
        context = PipelineContext.create("test.py", None, MigrationConfig())

        module = cst.parse_module("x = 1\ny = 'test'")

        # Mock _collect_top_level_assignments to raise an exception (covers lines 203-204)
        mocker.patch.object(
            step, "_collect_top_level_assignments", side_effect=ValueError("Assignment collection failed")
        )

        result = step.execute(context, module)
        # Should return error result when scanning fails
        assert result.is_error()
        assert "Failed to scan module" in str(result.error)

    def test_function_scanner_variable_analysis_error(self, mocker):
        """Test FunctionScannerStep handles variable analysis errors."""
        import libcst as cst

        from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
        from splurge_unittest_to_pytest.jobs.decision_analysis_job import FunctionScannerStep

        step = FunctionScannerStep("test_scanner", mocker.Mock())
        context = PipelineContext.create("test.py", None, MigrationConfig())

        # Set up required metadata
        from splurge_unittest_to_pytest.decision_model import ClassProposal, ModuleProposal

        class_prop = ClassProposal("TestClass", {})
        module_prop = ModuleProposal("test.py", {"TestClass": class_prop})
        context.metadata["module_proposal"] = module_prop

        module = cst.parse_module("""
class TestClass:
    def test_method(self):
        x = []
        x.append(1)
""")

        # Mock _is_variable_mutated to raise an exception
        mocker.patch.object(step, "_is_variable_mutated", side_effect=Exception("Mutation check failed"))

        result = step.execute(context, module)
        # Should succeed despite the error
        assert result.is_success()
