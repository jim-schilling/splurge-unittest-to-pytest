#!/usr/bin/env python3
"""Compare old heuristic detection vs new AST detection."""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent / "splurge_unittest_to_pytest"))

from splurge_unittest_to_pytest.detectors import UnittestFileDetector
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator


def test_heuristic_detection():
    """Test the old heuristic approach."""
    orchestrator = MigrationOrchestrator()

    test_files = [
        "false_positive_comments.py",
        "true_unittest.py",
        "import_only.py",
    ]

    print("=== HEURISTIC DETECTION RESULTS ===")
    for file_path in test_files:
        try:
            result = orchestrator._is_unittest_file(Path(file_path))
            print(f"{Path(file_path).name}: {result}")
        except Exception as e:
            print(f"{Path(file_path).name}: ERROR - {e}")


def test_ast_detection():
    """Test the new AST approach."""
    detector = UnittestFileDetector()

    test_files = [
        "false_positive_comments.py",
        "true_unittest.py",
        "import_only.py",
    ]

    print("\n=== AST DETECTION RESULTS ===")
    for file_path in test_files:
        try:
            result = detector.is_unittest_file(file_path)
            print(f"{Path(file_path).name}: {result}")
        except Exception as e:
            print(f"{Path(file_path).name}: ERROR - {e}")


if __name__ == "__main__":
    test_heuristic_detection()
    test_ast_detection()
