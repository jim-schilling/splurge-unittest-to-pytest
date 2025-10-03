"""Unit tests for custom exception classes.

This module tests the custom exception hierarchy for the decision
analysis system to ensure proper error handling and debugging information.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import pytest

from splurge_unittest_to_pytest.exceptions import (
    AnalysisStepError,
    ContextError,
    DecisionAnalysisError,
    ParametrizeConversionError,
    PatternDetectionError,
    ReconciliationError,
    TransformationError,
    TransformationValidationError,
)


class TestDecisionAnalysisError:
    """Test the base DecisionAnalysisError class."""

    def test_minimal_error_creation(self):
        """Test creating a minimal DecisionAnalysisError."""
        error = DecisionAnalysisError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_full_error_creation(self):
        """Test creating a DecisionAnalysisError with all context."""
        error = DecisionAnalysisError(
            "Analysis failed",
            analysis_step="function_scanner",
            function_name="test_func",
            class_name="TestClass",
            module_name="test_module.py",
        )

        assert error.message == "Analysis failed"
        expected_details = {
            "analysis_step": "function_scanner",
            "function_name": "test_func",
            "class_name": "TestClass",
            "module_name": "test_module.py",
        }
        assert error.details == expected_details


class TestAnalysisStepError:
    """Test the AnalysisStepError class."""

    def test_minimal_step_error(self):
        """Test creating a minimal AnalysisStepError."""
        error = AnalysisStepError("Step failed", "function_scanner")

        assert error.message == "Step failed"
        assert error.details == {"analysis_step": "function_scanner"}

    def test_full_step_error(self):
        """Test creating an AnalysisStepError with full context."""
        error = AnalysisStepError(
            "Function scan failed",
            "function_scanner",
            function_name="test_func",
            class_name="TestClass",
            module_name="test_module.py",
        )

        assert error.message == "Function scan failed"
        expected_details = {
            "analysis_step": "function_scanner",
            "function_name": "test_func",
            "class_name": "TestClass",
            "module_name": "test_module.py",
        }
        assert error.details == expected_details


class TestPatternDetectionError:
    """Test the PatternDetectionError class."""

    def test_minimal_pattern_error(self):
        """Test creating a minimal PatternDetectionError."""
        error = PatternDetectionError("Pattern not found", "subtest_loop")

        assert error.message == "Pattern not found"
        assert error.details == {"pattern_type": "subtest_loop"}

    def test_full_pattern_error(self):
        """Test creating a PatternDetectionError with full context."""
        error = PatternDetectionError(
            "SubTest pattern detection failed",
            "subtest_loop",
            function_name="test_func",
            class_name="TestClass",
            module_name="test_module.py",
        )

        assert error.message == "SubTest pattern detection failed"
        expected_details = {
            "pattern_type": "subtest_loop",
            "function_name": "test_func",
            "class_name": "TestClass",
            "module_name": "test_module.py",
        }
        assert error.details == expected_details


class TestReconciliationError:
    """Test the ReconciliationError class."""

    def test_minimal_reconciliation_error(self):
        """Test creating a minimal ReconciliationError."""
        error = ReconciliationError("Reconciliation failed", "strategy_conflict")

        assert error.message == "Reconciliation failed"
        assert error.details == {"conflict_type": "strategy_conflict"}

    def test_full_reconciliation_error(self):
        """Test creating a ReconciliationError with full context."""
        error = ReconciliationError(
            "Could not reconcile mixed strategies",
            "mixed_strategies",
            class_name="TestClass",
            module_name="test_module.py",
        )

        assert error.message == "Could not reconcile mixed strategies"
        expected_details = {
            "conflict_type": "mixed_strategies",
            "class_name": "TestClass",
            "module_name": "test_module.py",
        }
        assert error.details == expected_details


class TestContextError:
    """Test the ContextError class."""

    def test_minimal_context_error(self):
        """Test creating a minimal ContextError."""
        error = ContextError("Missing context", "module_proposal")

        assert error.message == "Missing context"
        assert error.details == {"required_context": "module_proposal"}

    def test_full_context_error(self):
        """Test creating a ContextError with full context."""
        error = ContextError("Required metadata not found", "module_proposal", "class_scanner")

        assert error.message == "Required metadata not found"
        expected_details = {"required_context": "module_proposal", "analysis_step": "class_scanner"}
        assert error.details == expected_details


class TestExceptionInheritance:
    """Test that exceptions properly inherit from MigrationError."""

    def test_decision_analysis_error_inheritance(self):
        """Test that DecisionAnalysisError inherits from MigrationError."""
        error = DecisionAnalysisError("Test error")

        # Should be an instance of both DecisionAnalysisError and MigrationError
        assert isinstance(error, DecisionAnalysisError)
        assert isinstance(error, Exception)

        # Should have message and details attributes
        assert hasattr(error, "message")
        assert hasattr(error, "details")

    def test_analysis_step_error_inheritance(self):
        """Test that AnalysisStepError inherits properly."""
        error = AnalysisStepError("Step failed", "test_step")

        assert isinstance(error, AnalysisStepError)
        assert isinstance(error, DecisionAnalysisError)
        assert isinstance(error, Exception)

    def test_pattern_detection_error_inheritance(self):
        """Test that PatternDetectionError inherits properly."""
        error = PatternDetectionError("Pattern failed", "test_pattern")

        assert isinstance(error, PatternDetectionError)
        assert isinstance(error, DecisionAnalysisError)
        assert isinstance(error, Exception)

    def test_reconciliation_error_inheritance(self):
        """Test that ReconciliationError inherits properly."""
        error = ReconciliationError("Reconciliation failed", "test_conflict")

        assert isinstance(error, ReconciliationError)
        assert isinstance(error, DecisionAnalysisError)
        assert isinstance(error, Exception)

    def test_context_error_inheritance(self):
        """Test that ContextError inherits properly."""
        error = ContextError("Context missing", "test_context")

        assert isinstance(error, ContextError)
        assert isinstance(error, DecisionAnalysisError)
        assert isinstance(error, Exception)


class TestTransformationError:
    """Test the TransformationError class."""

    def test_minimal_transformation_error(self):
        """Test creating a minimal TransformationError."""
        error = TransformationError("Transformation failed")

        assert error.message == "Transformation failed"
        assert error.details == {}

    def test_transformation_error_with_pattern(self):
        """Test creating a TransformationError with pattern type."""
        error = TransformationError("Assert rewrite failed", pattern_type="assert_equal")

        assert error.message == "Assert rewrite failed"
        assert error.details == {"pattern_type": "assert_equal"}


class TestTransformationValidationError:
    """Test the TransformationValidationError class."""

    def test_minimal_validation_error(self):
        """Test creating a minimal TransformationValidationError."""
        error = TransformationValidationError("CST validation failed")

        assert error.message == "CST validation failed"
        assert error.details == {"pattern_type": "validation"}

    def test_validation_error_inheritance(self):
        """Test that TransformationValidationError inherits properly."""
        error = TransformationValidationError("Validation failed")

        assert isinstance(error, TransformationValidationError)
        assert isinstance(error, TransformationError)
        assert isinstance(error, Exception)


class TestParametrizeConversionError:
    """Test the ParametrizeConversionError class."""

    def test_default_parametrize_error(self):
        """Test creating a ParametrizeConversionError with default message."""
        error = ParametrizeConversionError()

        assert error.message == "Cannot safely convert subTest loop to parametrize"
        assert error.details == {"pattern_type": "parametrize"}

    def test_custom_parametrize_error(self):
        """Test creating a ParametrizeConversionError with custom message."""
        error = ParametrizeConversionError("Custom parametrize error")

        assert error.message == "Custom parametrize error"
        assert error.details == {"pattern_type": "parametrize"}

    def test_parametrize_error_inheritance(self):
        """Test that ParametrizeConversionError inherits properly."""
        error = ParametrizeConversionError()

        assert isinstance(error, ParametrizeConversionError)
        assert isinstance(error, TransformationError)
        assert isinstance(error, Exception)
