"""
Hypothesis configuration for property-based testing.

This module configures Hypothesis settings for reproducible, performant,
and effective property-based testing in the splurge-unittest-to-pytest library.
"""

import hypothesis
from hypothesis import Phase, settings

# Configure Hypothesis globally for this test suite
hypothesis.settings.register_profile(
    "default",
    settings(
        # Reproducibility settings
        database=None,  # Disable database to avoid state between runs
        print_blob=True,  # Print minimal examples when tests fail
        # Performance settings
        max_examples=100,  # Reasonable number of examples per test
        deadline=None,  # No time limit per test (rely on overall test timeout)
        # Test phases - focus on finding bugs and shrinking
        phases=[
            Phase.explicit,  # Run explicit examples first
            Phase.reuse,  # Reuse previous failing examples
            Phase.generate,  # Generate new examples
            Phase.target,  # Target interesting values
            Phase.shrink,  # Shrink failing examples
        ],
        # Statefulness - disable for pure functions, enable for stateful tests
        stateful_step_count=50,  # Reasonable step count for stateful tests
        # Derandomization for reproducibility in CI
        derandomize=True,
    ),
)

hypothesis.settings.register_profile(
    "ci",
    settings(
        # CI-optimized settings - more thorough but still reasonable
        max_examples=200,  # More examples in CI
        deadline=None,
        print_blob=True,
        derandomize=True,
        phases=[
            Phase.explicit,
            Phase.reuse,
            Phase.generate,
            Phase.target,
            Phase.shrink,
        ],
    ),
)

hypothesis.settings.register_profile(
    "fast",
    settings(
        # Fast settings for development
        max_examples=50,  # Fewer examples for quick feedback
        deadline=None,
        print_blob=True,
        derandomize=True,
        phases=[
            Phase.explicit,
            Phase.reuse,
            Phase.generate,
            Phase.shrink,  # Skip target phase for speed
        ],
    ),
)

# Set default profile
hypothesis.settings.load_profile("default")

# Common settings that can be imported by test modules
DEFAULT_SETTINGS = settings(
    max_examples=100,
    deadline=None,
    print_blob=True,
    derandomize=True,
)

# Settings for stateful tests (transformers that maintain state)
STATEFUL_SETTINGS = settings(
    max_examples=50,  # Fewer examples for stateful tests
    deadline=None,
    print_blob=True,
    derandomize=True,
    stateful_step_count=30,
)

# Settings for performance-critical tests
PERFORMANCE_SETTINGS = settings(
    max_examples=20,  # Minimal examples for performance tests
    deadline=None,
    print_blob=True,
    derandomize=True,
)
