import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_generator_stage_composite_temp_dirs():
    module = cst.Module([])
    ci = ClassInfo(node=cst.ClassDef(name=cst.Name("MyTest"), body=cst.IndentedBlock(body=[])))
    # two dir-like attributes
    ci.setup_assignments["temp_dir"] = [cst.SimpleString('"/tmp/foo"')]
    ci.setup_assignments["config_dir"] = [cst.SimpleString('"/tmp/conf"')]
    # simulate a teardown statement existing
    ci.teardown_statements.append(cst.SimpleStatementLine(body=[cst.Pass()]))
    out = CollectorOutput(module=module, module_docstring_index=None, imports=[], classes={"MyTest": ci})

    ctx = {"collector_output": out, "use_generator_core": True}
    res = generator_stage(ctx)
    nodes = res.get("fixture_nodes") or []
    assert any(("def temp_dirs" in (n if isinstance(n, str) else str(n)) for n in nodes))
    # ensure yield-style emitted
    assert any(("yield" in (n if isinstance(n, str) else str(n)) for n in nodes))
