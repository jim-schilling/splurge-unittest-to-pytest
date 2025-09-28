import sys

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator

p = "tests/data/given_and_expected/unittest_given_09.txt"
orc = MigrationOrchestrator()
config = MigrationConfig(target_directory=".", backup_originals=False)
res = orc.migrate_file(p, config)
if res.is_success():
    print(res.data)
    sys.exit(0)
else:
    print("Migration failed:", res.error)
    sys.exit(2)
