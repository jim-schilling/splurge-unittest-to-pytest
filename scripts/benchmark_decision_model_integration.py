#!/usr/bin/env python3
"""Performance benchmark for decision model integration.

This script compares the performance of transformations with and without
the decision model to ensure the integration doesn't significantly impact
performance.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import tempfile
import time
from pathlib import Path

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator


def create_test_file() -> str:
    """Create a test unittest file for benchmarking."""
    content = """
import unittest

class TestExample(unittest.TestCase):
    def test_with_subtest_loop(self):
        test_cases = [
            ("input1", "expected1"),
            ("input2", "expected2"),
            ("input3", "expected3"),
        ]

        for case_input, expected in test_cases:
            with self.subTest(input=case_input):
                result = case_input.upper()
                self.assertEqual(result, expected)

    def test_another_subtest_loop(self):
        cases = [("a", 1), ("b", 2), ("c", 3)]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(len(value), expected)

    def test_accumulator_pattern(self):
        scenarios = []
        scenarios.append(("test1", "data1"))
        scenarios.append(("test2", "data2"))

        for scenario, data in scenarios:
            with self.subTest(scenario=scenario):
                self.assertIn(scenario, data)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        return f.name


def benchmark_transformation(
    orchestrator: MigrationOrchestrator, test_file: str, config: MigrationConfig, iterations: int = 10
) -> float:
    """Benchmark transformation performance."""
    times = []

    for _ in range(iterations):
        start_time = time.time()

        result = orchestrator.migrate_file(test_file, config)
        assert result.is_success()

        end_time = time.time()
        times.append(end_time - start_time)

    return sum(times) / len(times)


def main():
    """Run performance benchmarks."""
    print("Performance Benchmark: Decision Model Integration")
    print("=" * 50)

    test_file = create_test_file()

    try:
        orchestrator = MigrationOrchestrator()

        # Benchmark without decision model (baseline)
        print("Benchmarking without decision model...")
        config_baseline = MigrationConfig(use_decision_model=False)
        baseline_time = benchmark_transformation(orchestrator, test_file, config_baseline)
        print(f"Baseline (no decision model): {baseline_time:.4f} seconds")

        # Benchmark with decision model disabled in config but available
        print("Benchmarking with decision model disabled...")
        config_disabled = MigrationConfig(use_decision_model=False)
        disabled_time = benchmark_transformation(orchestrator, test_file, config_disabled)
        print(f"Disabled (use_decision_model=False): {disabled_time:.4f} seconds")

        # Benchmark with decision model enabled but no decision model available
        print("Benchmarking with decision model enabled but no model...")
        config_enabled_no_model = MigrationConfig(use_decision_model=True)
        enabled_no_model_time = benchmark_transformation(orchestrator, test_file, config_enabled_no_model)
        print(f"Enabled but no model: {enabled_no_model_time:.4f} seconds")

        # Calculate performance impact
        baseline_vs_disabled = ((disabled_time - baseline_time) / baseline_time) * 100
        baseline_vs_enabled_no_model = ((enabled_no_model_time - baseline_time) / baseline_time) * 100

        print("\nPerformance Impact:")
        print(f"  Decision model disabled: {baseline_vs_disabled:+.2f}%")
        print(f"  Decision model enabled (no model): {baseline_vs_enabled_no_model:+.2f}%")

        # Check if performance impact is acceptable (< 5% overhead)
        if baseline_vs_enabled_no_model > 5.0:
            print("Performance impact may be significant (> 5% overhead)")
        elif baseline_vs_enabled_no_model < -5.0:
            print("Performance improved significantly (> 5% faster)")
        else:
            print("Performance impact is acceptable (< 5%)")

    finally:
        # Clean up
        Path(test_file).unlink()


if __name__ == "__main__":
    main()
