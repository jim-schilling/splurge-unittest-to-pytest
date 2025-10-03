"""Tests for degradation functionality."""

from unittest.mock import Mock

import pytest

from splurge_unittest_to_pytest.degradation import (
    DegradationManager,
    DegradationResult,
    TransformationFailure,
    TransformationTier,
)
from splurge_unittest_to_pytest.result import Result


class TestTransformationTier:
    """Test TransformationTier enum."""

    def test_enum_values(self):
        """Test enum value definitions."""
        assert TransformationTier.ESSENTIAL.value == "essential"
        assert TransformationTier.ADVANCED.value == "advanced"
        assert TransformationTier.EXPERIMENTAL.value == "experimental"

    def test_enum_order(self):
        """Test enum ordering makes sense."""
        # Test that all enum values are unique and properly defined
        tiers = [TransformationTier.ESSENTIAL, TransformationTier.ADVANCED, TransformationTier.EXPERIMENTAL]
        values = [t.value for t in tiers]
        assert len(set(values)) == len(values)  # All values are unique
        assert "essential" in values
        assert "advanced" in values
        assert "experimental" in values


class TestTransformationFailure:
    """Test TransformationFailure dataclass."""

    def test_basic_creation(self):
        """Test basic failure creation."""
        failure = TransformationFailure(
            tier=TransformationTier.ADVANCED,
            transformation_name="test_transform",
            error_message="Test error",
        )

        assert failure.tier == TransformationTier.ADVANCED
        assert failure.transformation_name == "test_transform"
        assert failure.error_message == "Test error"
        assert failure.source_code is None
        assert failure.line_number is None
        assert failure.recovery_suggestion is None

    def test_full_creation(self):
        """Test failure creation with all fields."""
        failure = TransformationFailure(
            tier=TransformationTier.EXPERIMENTAL,
            transformation_name="complex_transform",
            error_message="Complex error occurred",
            source_code="def test(): pass",
            line_number=42,
            recovery_suggestion="Try simplifying the code",
        )

        assert failure.tier == TransformationTier.EXPERIMENTAL
        assert failure.transformation_name == "complex_transform"
        assert failure.error_message == "Complex error occurred"
        assert failure.source_code == "def test(): pass"
        assert failure.line_number == 42
        assert failure.recovery_suggestion == "Try simplifying the code"


class TestDegradationResult:
    """Test DegradationResult dataclass."""

    def test_success_result(self):
        """Test successful degradation result."""
        result = DegradationResult(
            original_result=Result.success("transformed"),
            degradation_applied=False,
            failures=[],
        )

        assert result.degradation_applied is False
        assert len(result.failures) == 0
        assert result.degraded_result is None
        assert result.recovery_attempts == 0

    def test_degraded_result(self):
        """Test result with degradation applied."""
        original = Result.failure(ValueError("original error"))
        degraded = Result.success("degraded_result")

        failures = [
            TransformationFailure(
                tier=TransformationTier.ADVANCED,
                transformation_name="test_transform",
                error_message="Transform failed",
            )
        ]

        result = DegradationResult(
            original_result=original,
            degradation_applied=True,
            failures=failures,
            degraded_result=degraded,
            recovery_attempts=2,
        )

        assert result.degradation_applied is True
        assert len(result.failures) == 1
        assert result.failures[0].transformation_name == "test_transform"
        assert result.degraded_result == degraded
        assert result.recovery_attempts == 2


class TestDegradationManager:
    """Test DegradationManager class."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = DegradationManager()
        assert manager.enabled is True
        assert manager.default_tier == TransformationTier.ADVANCED
        assert len(manager.failures) == 0

    def test_disabled_manager(self):
        """Test disabled degradation manager."""
        manager = DegradationManager(enabled=False)

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = True

        # Should still try the transformation but not apply degradation
        with pytest.raises(ValueError):
            manager.degrade_transformation("test", failing_func, config)

    def test_disabled_config(self):
        """Test degradation disabled via config."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = False

        # Should still try the transformation but not apply degradation
        with pytest.raises(ValueError):
            manager.degrade_transformation("test", failing_func, config)

    def test_successful_transformation(self):
        """Test degradation with successful transformation."""
        manager = DegradationManager()

        def success_func():
            return Result.success("success")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "advanced"

        result = manager.degrade_transformation("test", success_func, config)

        assert result.degradation_applied is False
        assert result.degraded_result is None  # No degradation applied
        assert len(result.failures) == 0

    def test_essential_degradation(self):
        """Test essential tier degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "essential"

        result = manager.degrade_transformation("assert_transform", failing_func, config)

        assert result.degradation_applied is True
        assert result.degraded_result.is_success()
        assert len(result.failures) == 1
        assert result.failures[0].tier == TransformationTier.ESSENTIAL
        assert result.recovery_attempts == 1

    def test_advanced_degradation(self):
        """Test advanced tier degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "advanced"

        result = manager.degrade_transformation("parametrize_transform", failing_func, config)

        assert result.degradation_applied is True
        assert result.degraded_result.is_success()
        assert len(result.failures) == 1
        assert result.failures[0].tier == TransformationTier.ADVANCED
        assert result.recovery_attempts == 2  # Essential + Advanced

    def test_experimental_degradation(self):
        """Test experimental tier degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "experimental"

        result = manager.degrade_transformation("unknown_transform", failing_func, config)

        assert result.degradation_applied is True
        assert result.degraded_result.is_success()
        assert len(result.failures) == 1
        assert result.failures[0].tier == TransformationTier.EXPERIMENTAL
        assert result.recovery_attempts == 3  # All tiers tried before succeeding with experimental

    def test_recovery_suggestions(self):
        """Test recovery suggestion generation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("complex expression error")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "advanced"

        result = manager.degrade_transformation("assert_transform", failing_func, config)

        assert len(result.failures) == 1
        failure = result.failures[0]
        assert "simplifying" in failure.recovery_suggestion.lower()

    def test_failure_tracking(self):
        """Test that failures are tracked across multiple calls."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "essential"

        # First degradation
        manager.degrade_transformation("transform1", failing_func, config)
        assert len(manager.failures) == 1

        # Second degradation
        manager.degrade_transformation("transform2", failing_func, config)
        assert len(manager.failures) == 2

        # Check failure summary
        summary = manager.get_failure_summary()
        assert summary["total_failures"] == 2
        assert summary["failures_by_transformation"]["transform1"] == 1
        assert summary["failures_by_transformation"]["transform2"] == 1

    def test_reset_functionality(self):
        """Test manager reset functionality."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("test error")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "essential"

        # Add some failures
        manager.degrade_transformation("test", failing_func, config)
        assert len(manager.failures) == 1

        # Reset
        manager.reset()
        assert len(manager.failures) == 0

        summary = manager.get_failure_summary()
        assert summary["total_failures"] == 0

    def test_config_tier_parsing(self):
        """Test configuration tier parsing."""
        manager = DegradationManager()

        config = Mock()
        config.degradation_enabled = True

        # Test string tier
        config.degradation_tier = "experimental"
        result = manager.degrade_transformation("test", lambda: Result.success("success"), config)
        assert result.degradation_applied is False  # Success, no degradation

        # Test enum tier
        config.degradation_tier = TransformationTier.ESSENTIAL
        result = manager.degrade_transformation("test", lambda: Result.success("success"), config)
        assert result.degradation_applied is False  # Success, no degradation
        assert len(result.failures) == 0


class TestDegradationStrategies:
    """Test specific degradation strategies."""

    def test_assert_degradation(self):
        """Test assert-specific degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("assert failed")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "essential"

        result = manager.degrade_transformation("assert_transform", failing_func, config, "test_code")

        assert result.degraded_result.is_success()
        assert "Essential degradation" in result.degraded_result.unwrap()

    def test_fixture_degradation(self):
        """Test fixture-specific degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("fixture failed")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "essential"

        result = manager.degrade_transformation("fixture_transform", failing_func, config)

        assert result.degraded_result.is_success()
        assert "setUp/tearDown" in result.degraded_result.unwrap()

    def test_parametrize_degradation(self):
        """Test parametrize-specific degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("parametrize failed")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "advanced"

        result = manager.degrade_transformation("parametrize_transform", failing_func, config)

        assert result.degraded_result.is_success()
        assert "kept subTest calls instead of parametrize" in result.degraded_result.unwrap()

    def test_complex_fixture_degradation(self):
        """Test complex fixture degradation."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("complex fixture failed")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "advanced"

        result = manager.degrade_transformation("complex_fixture_transform", failing_func, config)

        assert result.degraded_result.is_success()
        # Since it contains "fixture", it gets essential degradation, not advanced
        assert "kept original setUp/tearDown methods" in result.degraded_result.unwrap()

    def test_experimental_degradation(self):
        """Test experimental degradation fallback."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("experimental failed")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "experimental"

        result = manager.degrade_transformation("experimental_transform", failing_func, config)

        assert result.degraded_result.is_success()
        assert "Experimental degradation" in result.degraded_result.unwrap()


class TestIntegrationScenarios:
    """Test realistic degradation integration scenarios."""

    def test_multiple_tier_fallback(self):
        """Test fallback through multiple tiers."""
        manager = DegradationManager()

        def failing_func():
            raise ValueError("persistent failure")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "experimental"

        result = manager.degrade_transformation("persistent_transform", failing_func, config)

        # Should try essential -> advanced -> experimental
        assert result.recovery_attempts == 3  # All three tiers tried
        assert result.degradation_applied is True
        assert "Experimental degradation" in result.degraded_result.unwrap()

    def test_success_prevents_degradation(self):
        """Test that successful transformation prevents degradation."""
        manager = DegradationManager()

        def success_func():
            return Result.success("success")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "experimental"

        result = manager.degrade_transformation("success_transform", success_func, config)

        assert result.degradation_applied is False
        assert len(result.failures) == 0
        assert result.recovery_attempts == 0

    def test_detailed_failure_reporting(self):
        """Test detailed failure information collection."""
        manager = DegradationManager()

        def failing_func(*args, **kwargs):
            raise ValueError("detailed error message")

        config = Mock()
        config.degradation_enabled = True
        config.degradation_tier = "advanced"

        result = manager.degrade_transformation("detailed_transform", failing_func, config, "source_code", 42)

        assert len(result.failures) == 1
        failure = result.failures[0]
        assert failure.transformation_name == "detailed_transform"
        assert "detailed error message" in failure.error_message
        assert failure.tier == TransformationTier.ADVANCED
        assert failure.recovery_suggestion is not None
