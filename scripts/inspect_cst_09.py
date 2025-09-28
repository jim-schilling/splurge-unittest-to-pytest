import libcst as cst

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator

orc = MigrationOrchestrator()
config = MigrationConfig(target_directory=".", backup_originals=False, dry_run=True)
res = orc.migrate_file("tests/data/given_and_expected/unittest_given_09.txt", config)
if not res.is_success():
    print("migration failed", res.error)
    raise SystemExit(1)

code = res.metadata.get("generated_code")
print("--- generated code snippet for FileManager.create_file ---")
mod = cst.parse_module(code)
for node in mod.body:
    if isinstance(node, cst.ClassDef) and node.name.value == "FileManager":
        for stmt in node.body.body:
            # find create_file
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "create_file":
                print("Function create_file body statements:")
                for i, s in enumerate(stmt.body.body):
                    t = type(s).__name__
                    print(i, t, "->", getattr(s, "code", lambda: None)() if hasattr(s, "code") else "")
                raise SystemExit(0)
print("FileManager.create_file not found")
