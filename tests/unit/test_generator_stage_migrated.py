import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator as generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_generator_stage_delegation(tmp_path):
    # minimal collector output with one class and one setup assignment
    module = cst.Module([])
    ci = ClassInfo(node=cst.ClassDef(name=cst.Name("MyTest"), body=cst.IndentedBlock(body=[])))
    ci.setup_assignments["temp_dir"] = [cst.SimpleString('"/tmp/foo"')]
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"MyTest": ci})

    ctx = {"collector_output": out, "use_generator_core": True}
    res = generator_stage(ctx)
    nodes = res.get("fixture_nodes") or []
    assert nodes, "Expected fixture nodes from delegated GeneratorCore"
    # check golden-like content present (stringify nodes if needed)
    code_strings = [cst.Module([n]).code if not isinstance(n, str) else str(n) for n in nodes]
    assert any("def temp_dir" in s for s in code_strings)
