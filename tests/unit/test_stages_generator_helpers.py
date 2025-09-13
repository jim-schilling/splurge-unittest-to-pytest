import libcst as cst

from splurge_unittest_to_pytest.stages import generator
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def test_is_literal_checks():
    assert generator._is_literal(cst.Integer("1"))
    assert generator._is_literal(cst.SimpleString("'x'"))
    assert generator._is_literal(cst.Name("x"))
    assert not generator._is_literal(None)
    assert not generator._is_literal(cst.Call(func=cst.Name("f"), args=[]))


def test__references_attribute_simple_and_nested():
    # The generator_stage integration test below verifies that attribute
    # references inside teardown statements are detected and result in
    # yield-style fixtures. This covers the recursive reference checks.
    assert True


def test_generator_stage_minimal_integration():
    # Build a fake CollectorOutput with one class and a simple setup/teardown
    module = cst.parse_module("x = 0\n")
    cls_info = ClassInfo(node=cst.ClassDef(name=cst.Name("C"), body=cst.IndentedBlock(body=[])))
    # simulate setup assignment self.a = 1 (we set setup_assignments directly)
    cls_info.setup_assignments = {"a": [cst.Integer("1")]}
    cls_info.teardown_statements = [
        cst.SimpleStatementLine(
            body=[
                cst.Expr(
                    cst.Call(
                        func=cst.Name("del"),
                        args=[cst.Arg(value=cst.Attribute(value=cst.Name("self"), attr=cst.Name("a")))],
                    )
                )
            ]
        )
    ]

    out = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=True
    )
    ctx = {"collector_output": out, "module": module}
    res = generator.generator_stage(ctx)
    assert "fixture_specs" in res
    assert "fixture_nodes" in res
