"""Run MigrationOrchestrator in dry-run mode to produce expected outputs for given files 64-67.

This script is intended to be run locally in the development environment.
It will read the given files under tests/data/given_and_expected/* and write
corresponding pytest_expected_*.txt files containing the generated code.
"""

from pathlib import Path

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator


def main():
    base = Path("tests/data/given_and_expected")
    orchestrator = MigrationOrchestrator()

    for n in range(64, 70):
        given = base.joinpath(f"unittest_given_{n:02}.txt")
        expected = base.joinpath(f"pytest_expected_{n:02}.txt")
        if not given.exists():
            print(f"Skipping missing: {given}")
            continue

        cfg = MigrationConfig(dry_run=True)
        result = orchestrator.migrate_file(str(given), config=cfg)
        if result.is_success():
            generated = result.metadata.get("generated_code") if getattr(result, "metadata", None) else None
            if not generated:
                print(f"No generated code for {given}")
                continue
            expected.write_text(generated, encoding="utf-8")
            print(f"Wrote {expected}")
        else:
            print(f"Failed to migrate {given}: {result.error}")


if __name__ == "__main__":
    main()
