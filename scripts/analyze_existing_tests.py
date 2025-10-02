#!/usr/bin/env python3
"""Test utility for running decision analysis on existing test files.

This script analyzes existing unittest files using the decision analysis
pipeline and outputs the decision models for inspection and validation.

Usage:
    python scripts/analyze_existing_tests.py [--files FILE1 FILE2 ...]
    python scripts/analyze_existing_tests.py --test-suite  # Analyze all test files
    python scripts/analyze_existing_tests.py --examples  # Analyze example files

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import argparse
import json
import logging
from pathlib import Path

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.decision_model import DecisionModel
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.jobs.decision_analysis_job import DecisionAnalysisJob


def setup_logging() -> None:
    """Configure logging for the analysis utility."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def find_test_files() -> list[Path]:
    """Find all test files in the project."""
    project_root = Path(__file__).parent.parent

    # Look for test files in common locations
    test_dirs = [
        project_root / "tests",
        project_root / "test",
        project_root / "tests" / "unit",
        project_root / "tests" / "integration",
    ]

    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            # Find Python files that might contain tests
            for py_file in test_dir.rglob("test_*.py"):
                # Skip generated or temporary files
                if not any(part.startswith("__") or part.startswith(".") for part in py_file.parts):
                    test_files.append(py_file)

    return sorted(test_files)


def find_example_files() -> list[Path]:
    """Find example files in the project."""
    project_root = Path(__file__).parent.parent
    examples_dir = project_root / "examples"

    example_files = []
    if examples_dir.exists():
        for py_file in examples_dir.glob("*.py"):
            example_files.append(py_file)

    return sorted(example_files)


def analyze_file(file_path: Path) -> DecisionModel | None:
    """Analyze a single test file and return the decision model."""
    try:
        # Read the file content
        with open(file_path, encoding="utf-8") as f:
            source_code = f.read()

        # Skip empty files
        if not source_code.strip():
            print(f"[WARN] Skipping empty file: {file_path}")
            return None

        # Create analysis job
        event_bus = EventBus()
        job = DecisionAnalysisJob(event_bus)

        # Create context
        context = PipelineContext(
            source_file=str(file_path),
            target_file=None,
            config=MigrationConfig(enable_decision_analysis=True),
            run_id=f"analysis-{file_path.stem}",
            metadata={},
        )

        # Run analysis
        result = job.execute(context, source_code)

        if result.is_success():
            return result.data
        else:
            print(f"[ERROR] Analysis failed for {file_path}: {result.error}")
            return None

    except Exception as e:
        print(f"[ERROR] Error analyzing {file_path}: {e}")
        return None


def print_decision_model_summary(decision_model: DecisionModel, file_path: Path) -> None:
    """Print a summary of the decision model for a file."""
    print(f"\n[RESULTS] Analysis Results for {file_path.name}")
    print("=" * 50)

    for module_name, module_prop in decision_model.module_proposals.items():
        print(f"[MODULE] Module: {Path(module_name).name}")
        print(f"   Imports: {len(module_prop.module_imports)}")
        print(f"   Fixtures: {len(module_prop.module_fixtures)}")
        print(f"   Assignments: {len(module_prop.top_level_assignments)}")
        print(f"   Classes: {len(module_prop.class_proposals)}")

        for class_name, class_prop in module_prop.class_proposals.items():
            print(f"   [CLASS] Class: {class_name}")
            print(f"      Setup methods: {len(class_prop.class_setup_methods)}")
            print(f"      Fixtures: {len(class_prop.class_fixtures)}")
            print(f"      Functions: {len(class_prop.function_proposals)}")

            for func_name, func_prop in class_prop.function_proposals.items():
                print(f"      [FUNC] Function: {Path(func_name).name}")
                print(f"         Strategy: {func_prop.recommended_strategy}")
                print(f"         Evidence: {len(func_prop.evidence)} items")
                if func_prop.loop_var_name:
                    print(f"         Loop var: {func_prop.loop_var_name}")
                if func_prop.iterable_origin:
                    print(f"         Iterable: {func_prop.iterable_origin}")


def save_decision_model(decision_model: DecisionModel, file_path: Path, output_dir: Path) -> None:
    """Save the decision model to a JSON file."""
    output_file = output_dir / f"{file_path.stem}_analysis.json"

    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dict for JSON serialization
        data = {
            "module_proposals": {
                name: {
                    "module_name": prop.module_name,
                    "class_proposals": {
                        class_name: {
                            "class_name": class_prop.class_name,
                            "function_proposals": {
                                func_name: {
                                    "function_name": func_prop.function_name,
                                    "recommended_strategy": func_prop.recommended_strategy,
                                    "loop_var_name": func_prop.loop_var_name,
                                    "iterable_origin": func_prop.iterable_origin,
                                    "accumulator_mutated": func_prop.accumulator_mutated,
                                    "evidence": func_prop.evidence,
                                }
                                for func_name, func_prop in class_prop.function_proposals.items()
                            },
                            "class_fixtures": class_prop.class_fixtures,
                            "class_setup_methods": class_prop.class_setup_methods,
                        }
                        for class_name, class_prop in prop.class_proposals.items()
                    },
                    "module_fixtures": prop.module_fixtures,
                    "module_imports": prop.module_imports,
                    "top_level_assignments": prop.top_level_assignments,
                }
                for name, prop in decision_model.module_proposals.items()
            }
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[SAVED] Saved analysis to: {output_file}")

    except Exception as e:
        print(f"[ERROR] Failed to save analysis for {file_path}: {e}")


def compare_with_expected(file_path: Path, decision_model: DecisionModel) -> None:
    """Compare analysis results with expected outcomes (placeholder for future validation)."""
    print(f"\n[VALIDATION] Validation Check for {file_path.name}")

    # This is a placeholder for future validation logic
    # For now, just show that the analysis completed successfully
    total_functions = sum(
        len(class_prop.function_proposals)
        for module_prop in decision_model.module_proposals.values()
        for class_prop in module_prop.class_proposals.values()
    )

    print("   [OK] Analysis completed successfully")
    print(f"   [STATS] Analyzed {total_functions} functions")

    # Could add validation against expected results here
    # For example, check if certain patterns are detected correctly


def main():
    """Main entry point for the analysis utility."""
    parser = argparse.ArgumentParser(description="Run decision analysis on existing test files")
    parser.add_argument("--files", nargs="+", help="Specific files to analyze")
    parser.add_argument("--test-suite", action="store_true", help="Analyze all test files in the project")
    parser.add_argument("--examples", action="store_true", help="Analyze example files")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("analysis_output"), help="Directory to save analysis results"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    setup_logging()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which files to analyze
    files_to_analyze = []

    if args.files:
        files_to_analyze = [Path(f) for f in args.files]
    elif args.test_suite:
        files_to_analyze = find_test_files()
        print(f"[INFO] Found {len(files_to_analyze)} test files to analyze")
    elif args.examples:
        files_to_analyze = find_example_files()
        print(f"[INFO] Found {len(files_to_analyze)} example files to analyze")
    else:
        print("[ERROR] No files specified. Use --files, --test-suite, or --examples")
        return 1

    if not files_to_analyze:
        print("[ERROR] No files found to analyze")
        return 1

    print(f"[INFO] Starting analysis of {len(files_to_analyze)} files...")

    successful_analyses = 0
    failed_analyses = 0

    for file_path in files_to_analyze:
        print(f"\n[FILE] Analyzing: {file_path}")

        decision_model = analyze_file(file_path)

        if decision_model:
            successful_analyses += 1
            print_decision_model_summary(decision_model, file_path)
            compare_with_expected(file_path, decision_model)

            if args.output_dir:
                save_decision_model(decision_model, file_path, args.output_dir)
        else:
            failed_analyses += 1

    # Print summary
    print("\n[COMPLETE] Analysis Complete!")
    print(f"   [SUCCESS] Successful: {successful_analyses}")
    print(f"   [FAILED] Failed: {failed_analyses}")
    print(f"   [TOTAL] Total: {len(files_to_analyze)}")

    return 0 if failed_analyses == 0 else 1


if __name__ == "__main__":
    exit(main())
