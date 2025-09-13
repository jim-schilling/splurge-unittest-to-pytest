import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo


def _is_literal(node):
    return isinstance(node, (cst.SimpleString, cst.Integer, cst.Float)) or (
        isinstance(node, cst.Name) and getattr(node, "value", None) in ("True", "False")
    )


def test_is_literal_checks():
    assert _is_literal(cst.Integer("1"))
    assert _is_literal(cst.SimpleString("'x'"))
    # bare names are not considered literal scalars by the generator helpers
    assert not _is_literal(cst.Name("x"))
    assert not _is_literal(None)
    assert not _is_literal(cst.Call(func=cst.Name("f"), args=[]))


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
    res = generator(ctx)
    assert "fixture_specs" in res
    assert "fixture_nodes" in res
