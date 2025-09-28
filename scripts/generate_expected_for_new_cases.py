import glob

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator

orchestrator = MigrationOrchestrator()

files = sorted(glob.glob("tests/data/given_and_expected/unittest_given_2*.txt"))
for f in files:
    cfg = MigrationConfig(target_directory=".", backup_originals=False)
    res = orchestrator.migrate_file(f, cfg)
    out_name = f.replace("unittest_given_", "pytest_expected_")
    if res.is_success():
        with open(out_name, "w", encoding="utf-8") as fh:
            fh.write(res.data)
        print("WROTE", out_name)
    else:
        print("FAILED", f, res.error)
