"""Comprehensive tests for the Advanced Error Reporting System.

This module tests all components of the error reporting system including
error classification, severity assessment, suggestion generation, and
recovery workflows.
"""

from unittest.mock import Mock

import pytest

from splurge_unittest_to_pytest.error_reporting import (
    ErrorCategory,
    ErrorRecoveryAssistant,
    ErrorReporter,
    ErrorSeverity,
    ErrorSeverityAssessor,
    ErrorSuggestionEngine,
    RecoveryStep,
    RecoveryWorkflow,
    SmartError,
    Suggestion,
)


class TestErrorCategory:
    """Test error category enumeration."""

    def test_error_categories_exist(self):
        """Test that all expected error categories are defined."""
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.FILESYSTEM.value == "filesystem"
        assert ErrorCategory.PARSING.value == "parsing"
        assert ErrorCategory.TRANSFORMATION.value == "transformation"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.DEPENDENCY.value == "dependency"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorSeverity:
    """Test error severity enumeration."""

    def test_error_severities_exist(self):
        """Test that all expected error severities are defined."""
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.INFO.value == "info"


class TestSuggestion:
    """Test suggestion dataclass."""

    def test_suggestion_creation(self):
        """Test creating a suggestion."""
        suggestion = Suggestion(
            message="Test message", action="Test action", examples=["example1", "example2"], priority=2, category="test"
        )

        assert suggestion.message == "Test message"
        assert suggestion.action == "Test action"
        assert suggestion.examples == ["example1", "example2"]
        assert suggestion.priority == 2
        assert suggestion.category == "test"

    def test_suggestion_defaults(self):
        """Test suggestion default values."""
        suggestion = Suggestion(message="Test", action="Action")

        assert suggestion.examples is None
        assert suggestion.priority == 1
        assert suggestion.category is None

    def test_suggestion_to_dict(self):
        """Test converting suggestion to dictionary."""
        suggestion = Suggestion(
            message="Test message", action="Test action", examples=["example"], priority=1, category="test"
        )

        result = suggestion.to_dict()

        expected = {
            "message": "Test message",
            "action": "Test action",
            "examples": ["example"],
            "priority": 1,
            "category": "test",
        }

        assert result == expected


class TestSmartError:
    """Test SmartError class."""

    def test_smart_error_creation(self):
        """Test creating a SmartError."""
        error = SmartError(
            message="Test error",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context={"field": "test"},
            suggestions=[
                Suggestion(message="Fix config", action="Update config"),
            ],
            recovery_actions=["action1", "action2"],
        )

        assert error.message == "Test error"
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == {"field": "test"}
        assert len(error.suggestions) == 1
        assert error.recovery_actions == ["action1", "action2"]

    def test_smart_error_defaults(self):
        """Test SmartError default values."""
        error = SmartError(message="Test error")

        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context == {}
        assert error.suggestions == []
        assert error.recovery_actions == []

    def test_add_suggestion(self):
        """Test adding suggestions to SmartError."""
        error = SmartError(message="Test")

        suggestion = Suggestion(message="New suggestion", action="Action")
        error.add_suggestion(suggestion)

        assert len(error.suggestions) == 1
        assert error.suggestions[0].message == "New suggestion"
        assert error.details["suggestions"][0]["message"] == "New suggestion"

    def test_get_prioritized_suggestions(self):
        """Test getting suggestions sorted by priority."""
        error = SmartError(message="Test")

        # Add suggestions with different priorities
        error.add_suggestion(Suggestion(message="High priority", action="Action", priority=1))
        error.add_suggestion(Suggestion(message="Low priority", action="Action", priority=3))
        error.add_suggestion(Suggestion(message="Medium priority", action="Action", priority=2))

        suggestions = error.get_prioritized_suggestions()

        assert len(suggestions) == 3
        assert suggestions[0].message == "High priority"  # Priority 1 first
        assert suggestions[1].message == "Medium priority"  # Priority 2 second
        assert suggestions[2].message == "Low priority"  # Priority 3 last

    def test_is_recoverable(self):
        """Test checking if error is recoverable."""
        # Configuration errors should be recoverable
        config_error = SmartError(message="Config error", category=ErrorCategory.CONFIGURATION)
        assert config_error.is_recoverable()

        # Filesystem errors should be recoverable
        fs_error = SmartError(message="FS error", category=ErrorCategory.FILESYSTEM)
        assert fs_error.is_recoverable()

        # Permission errors should be recoverable
        perm_error = SmartError(message="Permission error", category=ErrorCategory.PERMISSION)
        assert perm_error.is_recoverable()

        # Transformation errors should NOT be recoverable
        trans_error = SmartError(message="Transform error", category=ErrorCategory.TRANSFORMATION)
        assert not trans_error.is_recoverable()

    def test_to_user_friendly_message(self):
        """Test generating user-friendly error message."""
        error = SmartError(
            message="Configuration error",
            severity=ErrorSeverity.HIGH,
            suggestions=[
                Suggestion(message="Fix the config", action="Update target_root"),
            ],
            recovery_actions=["Run with --dry-run"],
        )

        message = error.to_user_friendly_message()

        assert "[HIGH]" in message
        assert "Configuration error" in message
        assert "Suggestions:" in message
        assert "Fix the config" in message
        assert "Next steps:" in message
        assert "Run with --dry-run" in message


class TestErrorSeverityAssessor:
    """Test error severity assessment."""

    def test_assess_severity_with_context_indicators(self):
        """Test severity assessment based on context indicators."""
        assessor = ErrorSeverityAssessor()

        # Test file not found context
        error = Exception("File not found")
        context = {"file_not_found": True}
        severity = assessor.assess_severity(error, context)

        assert severity == ErrorSeverity.HIGH

    def test_assess_severity_with_smart_error(self):
        """Test severity assessment for SmartError."""
        assessor = ErrorSeverityAssessor()

        # Test configuration error severity
        error = SmartError(message="Config error", category=ErrorCategory.CONFIGURATION)
        severity = assessor.assess_severity(error)

        assert severity == ErrorSeverity.HIGH

    def test_assess_severity_with_regular_exception(self):
        """Test severity assessment for regular exceptions."""
        assessor = ErrorSeverityAssessor()

        # Test permission error inference
        error = Exception("Permission denied")
        severity = assessor.assess_severity(error)

        assert severity == ErrorSeverity.HIGH

    def test_assess_severity_fallback(self):
        """Test fallback severity assessment."""
        assessor = ErrorSeverityAssessor()

        # Test unknown error type
        error = Exception("Unknown error")
        severity = assessor.assess_severity(error)

        assert severity == ErrorSeverity.MEDIUM


class TestErrorSuggestionEngine:
    """Test error suggestion generation."""

    def test_generate_suggestions_for_config_error(self):
        """Test generating suggestions for configuration errors."""
        engine = ErrorSuggestionEngine()

        error = SmartError(message="Invalid file pattern: test_[.py", category=ErrorCategory.CONFIGURATION)

        suggestions = engine.generate_suggestions(error)

        assert len(suggestions) > 0

        # Should have file pattern suggestion
        pattern_suggestion = next((s for s in suggestions if "pattern" in s.message.lower()), None)
        assert pattern_suggestion is not None

    def test_generate_suggestions_for_filesystem_error(self):
        """Test generating suggestions for filesystem errors."""
        engine = ErrorSuggestionEngine()

        error = SmartError(message="No such file or directory: /invalid/path", category=ErrorCategory.FILESYSTEM)

        suggestions = engine.generate_suggestions(error)

        assert len(suggestions) > 0

        # Should have file existence suggestion
        file_suggestion = next((s for s in suggestions if "does not exist" in s.message), None)
        assert file_suggestion is not None

    def test_generate_suggestions_for_permission_error(self):
        """Test generating suggestions for permission errors."""
        engine = ErrorSuggestionEngine()

        error = SmartError(message="Permission denied: /restricted/file.py", category=ErrorCategory.PERMISSION)

        suggestions = engine.generate_suggestions(error)

        assert len(suggestions) > 0

        # Should have permission suggestion
        perm_suggestion = next((s for s in suggestions if "permission" in s.message.lower()), None)
        assert perm_suggestion is not None

    def test_generate_suggestions_with_context(self):
        """Test generating suggestions with error context."""
        engine = ErrorSuggestionEngine()

        error = SmartError(
            message="Error in file", category=ErrorCategory.TRANSFORMATION, context={"line": 42, "column": 10}
        )

        suggestions = engine.generate_suggestions(error)

        # Debug: print all suggestions
        print(f"Generated {len(suggestions)} suggestions:")
        for s in suggestions:
            print(f"  - {s.message}")

        # Should have context suggestion
        context_suggestion = next((s for s in suggestions if "line" in s.message.lower()), None)
        print(f"Context suggestion found: {context_suggestion is not None}")
        assert context_suggestion is not None

    def test_suggestion_deduplication(self):
        """Test that duplicate suggestions are removed."""
        engine = ErrorSuggestionEngine()

        # Create error that would generate multiple similar suggestions
        error = SmartError(message="File not found and permission denied", category=ErrorCategory.FILESYSTEM)

        suggestions = engine.generate_suggestions(error)

        # Check for duplicates by comparing message+action pairs
        seen = set()
        for suggestion in suggestions:
            key = (suggestion.message, suggestion.action)
            assert key not in seen
            seen.add(key)


class TestRecoveryStep:
    """Test recovery step dataclass."""

    def test_recovery_step_creation(self):
        """Test creating a recovery step."""
        step = RecoveryStep(
            description="Test step", action="Test action", examples=["example"], validation="Test validation"
        )

        assert step.description == "Test step"
        assert step.action == "Test action"
        assert step.examples == ["example"]
        assert step.validation == "Test validation"

    def test_recovery_step_to_dict(self):
        """Test converting recovery step to dictionary."""
        step = RecoveryStep(description="Test", action="Action")

        result = step.to_dict()

        expected = {
            "description": "Test",
            "action": "Action",
            "examples": [],
            "validation": None,
        }

        assert result == expected


class TestRecoveryWorkflow:
    """Test recovery workflow dataclass."""

    def test_recovery_workflow_creation(self):
        """Test creating a recovery workflow."""
        workflow = RecoveryWorkflow(
            title="Test Workflow",
            description="Test description",
            steps=[
                RecoveryStep(description="Step 1", action="Action 1"),
            ],
            estimated_time="5 minutes",
            success_rate=0.9,
        )

        assert workflow.title == "Test Workflow"
        assert workflow.description == "Test description"
        assert len(workflow.steps) == 1
        assert workflow.estimated_time == "5 minutes"
        assert workflow.success_rate == 0.9

    def test_recovery_workflow_to_dict(self):
        """Test converting recovery workflow to dictionary."""
        workflow = RecoveryWorkflow(title="Test", steps=[RecoveryStep(description="Step", action="Action")])

        result = workflow.to_dict()

        expected = {
            "title": "Test",
            "description": None,
            "steps": [
                {
                    "description": "Step",
                    "action": "Action",
                    "examples": [],
                    "validation": None,
                }
            ],
            "estimated_time": None,
            "success_rate": None,
        }

        assert result == expected


class TestErrorRecoveryAssistant:
    """Test error recovery assistant."""

    def test_suggest_recovery_workflow_for_config_error(self):
        """Test suggesting recovery workflow for configuration errors."""
        assistant = ErrorRecoveryAssistant()

        error = SmartError(message="Config error", category=ErrorCategory.CONFIGURATION)
        workflow = assistant.suggest_recovery_workflow(error)

        assert workflow is not None
        assert workflow.title == "Configuration Issue Recovery"

    def test_suggest_recovery_workflow_for_filesystem_error(self):
        """Test suggesting recovery workflow for filesystem errors."""
        assistant = ErrorRecoveryAssistant()

        error = SmartError(message="FS error", category=ErrorCategory.FILESYSTEM)
        workflow = assistant.suggest_recovery_workflow(error)

        assert workflow is not None
        assert workflow.title == "File System Issue Recovery"

    def test_suggest_recovery_workflow_for_permission_error(self):
        """Test suggesting recovery workflow for permission errors."""
        assistant = ErrorRecoveryAssistant()

        error = SmartError(message="Permission error", category=ErrorCategory.PERMISSION)
        workflow = assistant.suggest_recovery_workflow(error)

        assert workflow is not None
        assert workflow.title == "Permission Issue Recovery"

    def test_suggest_recovery_workflow_for_transformation_error(self):
        """Test suggesting recovery workflow for transformation errors."""
        assistant = ErrorRecoveryAssistant()

        error = SmartError(message="Transform error", category=ErrorCategory.TRANSFORMATION)
        workflow = assistant.suggest_recovery_workflow(error)

        assert workflow is not None
        assert workflow.title == "Transformation Issue Recovery"

    def test_no_workflow_for_unknown_error(self):
        """Test that no workflow is suggested for unknown errors."""
        assistant = ErrorRecoveryAssistant()

        error = SmartError(message="Completely unknown error", category=ErrorCategory.UNKNOWN)
        workflow = assistant.suggest_recovery_workflow(error)

        assert workflow is None


class TestErrorReporter:
    """Test central error reporting system."""

    def test_enhance_basic_exception(self):
        """Test enhancing a basic exception."""
        reporter = ErrorReporter()

        error = ValueError("Basic error")
        context = {"test": "context"}

        smart_error = reporter.enhance_error(error, context)

        assert isinstance(smart_error, SmartError)
        assert smart_error.category == ErrorCategory.UNKNOWN
        assert smart_error.context == context

    def test_enhance_smart_error_passthrough(self):
        """Test that SmartErrors are passed through unchanged."""
        reporter = ErrorReporter()

        original_error = SmartError(message="Smart error", category=ErrorCategory.CONFIGURATION)

        enhanced_error = reporter.enhance_error(original_error)

        assert enhanced_error is original_error

    def test_report_error_comprehensive(self):
        """Test generating comprehensive error report."""
        reporter = ErrorReporter()

        # Use a filesystem error that should have a workflow
        error = FileNotFoundError("No such file or directory: test.py")
        context = {"file": "test.py", "line": 42}

        report = reporter.report_error(error, context, include_workflow=True)

        assert "error" in report
        assert "message" in report["error"]
        assert "category" in report["error"]
        assert "severity" in report["error"]
        assert "context" in report["error"]
        assert "suggestions" in report["error"]
        assert "recovery_actions" in report["error"]
        assert "is_recoverable" in report["error"]
        assert "recovery_workflow" in report

    def test_get_recovery_workflow(self):
        """Test getting recovery workflow for error."""
        reporter = ErrorReporter()

        error = SmartError(message="Config error", category=ErrorCategory.CONFIGURATION)
        workflow = reporter.get_recovery_workflow(error)

        assert workflow is not None
        assert workflow.title == "Configuration Issue Recovery"


class TestIntegration:
    """Integration tests for the error reporting system."""

    def test_end_to_end_error_reporting(self):
        """Test complete error reporting workflow."""
        reporter = ErrorReporter()

        # Simulate a configuration error
        original_error = ValueError("Invalid configuration: target_root does not exist")
        context = {"target_root": "/nonexistent/path"}

        # Generate comprehensive report
        report = reporter.report_error(original_error, context)

        # Verify report structure
        assert report["error"]["category"] == ErrorCategory.FILESYSTEM.value
        assert report["error"]["severity"] == ErrorSeverity.HIGH.value
        assert len(report["error"]["suggestions"]) > 0
        assert report["error"]["is_recoverable"] is True

        # Verify workflow is included
        assert "recovery_workflow" in report
        workflow = report["recovery_workflow"]
        assert workflow["title"] == "File System Issue Recovery"

    def test_error_enhancement_with_suggestions(self):
        """Test that error enhancement includes relevant suggestions."""
        reporter = ErrorReporter()

        # Create error that should generate specific suggestions
        error = FileNotFoundError("No such file or directory: /missing/file.py")
        context = {"file_path": "/missing/file.py"}

        enhanced_error = reporter.enhance_error(error, context)

        # Should have filesystem-related suggestions
        assert len(enhanced_error.suggestions) > 0

        # Check for relevant suggestion types
        suggestion_messages = [s.message.lower() for s in enhanced_error.suggestions]
        assert any("does not exist" in msg for msg in suggestion_messages)

    def test_recovery_workflow_generation(self):
        """Test that appropriate recovery workflows are generated."""
        reporter = ErrorReporter()

        # Test configuration error workflow
        config_error = SmartError(message="Config issue", category=ErrorCategory.CONFIGURATION)
        workflow = reporter.get_recovery_workflow(config_error)

        assert workflow is not None
        assert len(workflow.steps) > 0

        # Check that steps have required fields
        for step in workflow.steps:
            assert step.description
            assert step.action


# Mock classes for testing (to avoid import issues)
class FileNotFoundError(Exception):
    """Mock FileNotFoundError for testing."""

    pass
