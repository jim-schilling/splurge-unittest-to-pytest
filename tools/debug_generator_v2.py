import libcst as cst
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo
from splurge_unittest_to_pytest.stages.generator import generator

module = cst.Module([])
ci = ClassInfo(node=cst.ClassDef(name=cst.Name("TestDirs"), body=cst.IndentedBlock(body=[])))
attrs = {
    "temp_dir": cst.Call(func=cst.Attribute(value=cst.Name("tempfile"), attr=cst.Name("mkdtemp")), args=[]),
    "config_dir": cst.Call(
        func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]
    ),
    "data_dir": cst.Call(
        func=cst.Name("Path"), args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))]
    ),
}
for k, v in attrs.items():
    ci.setup_assignments[k] = [v]
teardown = [
    cst.SimpleStatementLine(
        body=[
            cst.Expr(
                cst.Call(
                    func=cst.Attribute(value=cst.Name("shutil"), attr=cst.Name("rmtree")),
                    args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("temp_dir")))],
                )
            )
        ]
    )
]
ci.teardown_statements = teardown
out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"TestDirs": ci})
res = generator({"collector_output": out})
print("keys:", list(res.keys()))
fnodes = [n for n in res.get("fixture_nodes", []) if isinstance(n, cst.FunctionDef)]
print("fixture count:", len(fnodes))
for n in fnodes:
    print("fixture name:", n.name.value)
    print(cst.Module(body=[n]).code)

# show needs_shutil flag
print("needs_shutil_import:", res.get("needs_shutil_import"))
print("needs_typing:", res.get("needs_typing_names"))
