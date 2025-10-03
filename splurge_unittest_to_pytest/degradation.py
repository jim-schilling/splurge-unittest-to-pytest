"""Gradual degradation system for transformation failures.

This module implements tiered transformation strategies that allow the system
to gracefully degrade when complex transformations fail, ensuring maximum
code conversion while providing clear feedback about what couldn't be transformed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .result import Result

logger = logging.getLogger(__name__)


class TransformationTier(Enum):
    """Transformation complexity tiers."""

    ESSENTIAL = "essential"  # Basic assert conversions, TestCase removal
    ADVANCED = "advanced"  # Fixture generation, subtest conversion
    EXPERIMENTAL = "experimental"  # Complex assertion patterns, regex handling


@dataclass
class TransformationFailure:
    """Record of a transformation failure."""

    tier: TransformationTier
    transformation_name: str
    error_message: str
    source_code: str | None = None
    line_number: int | None = None
    recovery_suggestion: str | None = None


@dataclass
class DegradationResult:
    """Result of a degradation attempt."""

    original_result: Result[Any]
    degradation_applied: bool
    failures: list[TransformationFailure]
    degraded_result: Result[Any] | None = None
    recovery_attempts: int = 0


class DegradationManager:
    """Manages gradual degradation of transformations."""

    def __init__(self, enabled: bool = True, default_tier: TransformationTier = TransformationTier.ADVANCED):
        self.enabled = enabled
        self.default_tier = default_tier
        self.failures: list[TransformationFailure] = []

    def degrade_transformation(
        self, transformation_name: str, transformation_func: Callable[..., Result[Any]], config: Any, *args, **kwargs
    ) -> DegradationResult:
        """Apply degradation strategy to a transformation.

        Args:
            transformation_name: Name of the transformation
            transformation_func: The transformation function to call
            config: Configuration object with degradation settings
            *args, **kwargs: Arguments to pass to the transformation

        Returns:
            DegradationResult with original/degraded results and failure info
        """
        if not self.enabled or not getattr(config, "degradation_enabled", True):
            # Degradation disabled, run normally
            result = transformation_func(*args, **kwargs)
            return DegradationResult(original_result=result, degradation_applied=False, failures=[])

        # Determine target tier
        target_tier = getattr(config, "degradation_tier", self.default_tier.value)
        if isinstance(target_tier, str):
            target_tier = TransformationTier(target_tier)

        # Try transformation with degradation
        return self._apply_degradation(transformation_name, transformation_func, target_tier, config, *args, **kwargs)

    def _apply_degradation(
        self,
        transformation_name: str,
        transformation_func: Callable[..., Result[Any]],
        target_tier: TransformationTier,
        config: Any,
        *args,
        **kwargs,
    ) -> DegradationResult:
        """Apply degradation logic."""

        # Try the full transformation first
        try:
            result = transformation_func(*args, **kwargs)
            if result.is_success():
                return DegradationResult(original_result=result, degradation_applied=False, failures=[])
        except Exception as e:
            result = Result.failure(e)

        # If we reach here, the full transformation failed
        # Apply degradation based on the target tier
        failures = []
        recovery_attempts = 0

        if target_tier == TransformationTier.ESSENTIAL:
            # Essential tier: Try minimal fallback
            degraded_result = self._apply_essential_degradation(transformation_name, result, config, *args, **kwargs)
            recovery_attempts += 1

        elif target_tier == TransformationTier.ADVANCED:
            # Advanced tier: Try essential + advanced fallbacks
            degraded_result = self._apply_essential_degradation(transformation_name, result, config, *args, **kwargs)
            if degraded_result and degraded_result.is_success():
                recovery_attempts += 1
            else:
                degraded_result = self._apply_advanced_degradation(transformation_name, result, config, *args, **kwargs)
                recovery_attempts += 2

        else:  # EXPERIMENTAL
            # Experimental tier: Try all degradation strategies
            degraded_result = self._apply_essential_degradation(transformation_name, result, config, *args, **kwargs)
            recovery_attempts += 1

            if not (degraded_result and degraded_result.is_success()):
                degraded_result = self._apply_advanced_degradation(transformation_name, result, config, *args, **kwargs)
                recovery_attempts += 1

                if not (degraded_result and degraded_result.is_success()):
                    degraded_result = self._apply_experimental_degradation(
                        transformation_name, result, config, *args, **kwargs
                    )
                    recovery_attempts += 1

        # Record the failure
        failure = TransformationFailure(
            tier=target_tier,
            transformation_name=transformation_name,
            error_message=str(result.error) if result.error else "Unknown error",
            recovery_suggestion=self._generate_recovery_suggestion(transformation_name, result),
        )
        failures.append(failure)
        self.failures.append(failure)

        return DegradationResult(
            original_result=result,
            degradation_applied=degraded_result is not None and degraded_result.is_success(),
            failures=failures,
            degraded_result=degraded_result,
            recovery_attempts=recovery_attempts,
        )

    def _apply_essential_degradation(
        self, transformation_name: str, failed_result: Result[Any], config: Any, *args, **kwargs
    ) -> Result[Any] | None:
        """Apply essential-level degradation (minimal fallbacks)."""

        # For assert transformations, essential degradation means keeping basic asserts
        if "assert" in transformation_name.lower():
            # Return the original code unchanged - better than failing completely
            if args and hasattr(args[0], "code"):
                return Result.success(args[0].code)
            return Result.success("# Essential degradation: kept original assertion")

        # For fixture transformations, essential means keeping setUp/tearDown as-is
        if "fixture" in transformation_name.lower():
            return Result.success("# Essential degradation: kept original setUp/tearDown methods")

        return None

    def _apply_advanced_degradation(
        self, transformation_name: str, failed_result: Result[Any], config: Any, *args, **kwargs
    ) -> Result[Any] | None:
        """Apply advanced-level degradation."""

        # For complex transformations, try simpler alternatives
        if "parametrize" in transformation_name.lower():
            # If parametrize fails, keep as regular subTest calls
            return Result.success("# Advanced degradation: kept subTest calls instead of parametrize")

        if "fixture" in transformation_name.lower() and "complex" in transformation_name.lower():
            # If complex fixtures fail, generate basic fixtures
            return Result.success("# Advanced degradation: generated basic fixtures")

        return None

    def _apply_experimental_degradation(
        self, transformation_name: str, failed_result: Result[Any], config: Any, *args, **kwargs
    ) -> Result[Any] | None:
        """Apply experimental-level degradation (riskier fallbacks)."""

        # For experimental features, we might try very basic transformations
        # or just comment out the problematic code
        return Result.success(f"# Experimental degradation: commented out failed {transformation_name}")

    def _generate_recovery_suggestion(self, transformation_name: str, failed_result: Result[Any]) -> str:
        """Generate user-friendly recovery suggestions."""

        error_msg = str(failed_result.error) if failed_result.error else ""

        if "assert" in transformation_name.lower():
            if "complex" in error_msg.lower():
                return "Consider simplifying the assertion or using assert statement directly"
            return "Check assertion syntax and argument types"

        if "fixture" in transformation_name.lower():
            return "Review setUp/tearDown method complexity or convert manually"

        if "parametrize" in transformation_name.lower():
            return "Check subTest loop structure or convert to manual parametrization"

        return f"Review {transformation_name} for syntax errors or unsupported patterns"

    def get_failure_summary(self) -> dict[str, Any]:
        """Get a summary of all transformation failures."""

        summary = {
            "total_failures": len(self.failures),
            "failures_by_tier": {},
            "failures_by_transformation": {},
            "recovery_suggestions": [],
        }

        for failure in self.failures:
            # Count by tier
            tier_key = failure.tier.value
            summary["failures_by_tier"][tier_key] = summary["failures_by_tier"].get(tier_key, 0) + 1  # type: ignore[index,attr-defined]

            # Count by transformation
            summary["failures_by_transformation"][failure.transformation_name] = (  # type: ignore[index]
                summary["failures_by_transformation"].get(failure.transformation_name, 0) + 1  # type: ignore[attr-defined]
            )

            # Collect suggestions
            if failure.recovery_suggestion:
                summary["recovery_suggestions"].append(  # type: ignore[attr-defined]
                    {
                        "transformation": failure.transformation_name,
                        "suggestion": failure.recovery_suggestion,
                        "error": failure.error_message,
                    }
                )

        return summary

    def reset(self):
        """Reset the degradation manager state."""
        self.failures.clear()
