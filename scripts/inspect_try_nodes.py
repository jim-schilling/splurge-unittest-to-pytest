import libcst as cst

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator

orc = MigrationOrchestrator()
config = MigrationConfig(target_root=".", backup_originals=False, dry_run=True)
res = orc.migrate_file("tests/data/given_and_expected/unittest_given_09.txt", config)
code = res.metadata.get("generated_code")
mod = cst.parse_module(code)
for node in mod.body:
    if isinstance(node, cst.ClassDef) and node.name.value == "FileManager":
        for func in node.body.body:
            if isinstance(func, cst.FunctionDef) and func.name.value == "create_file":
                for stmt in func.body.body:
                    print("STMT TYPE:", type(stmt).__name__)
                    print("CODE:\n", stmt.code)
                    if isinstance(stmt, cst.Try):
                        print("Try body items:")
                        for j, inner in enumerate(stmt.body.body):
                            print("  INNER", j, type(inner).__name__)
                            print(inner.code)
                raise SystemExit(0)
print("Done")
