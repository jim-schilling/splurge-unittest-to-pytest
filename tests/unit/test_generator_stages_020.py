import libcst as cst

from splurge_unittest_to_pytest.stages.generator import generator as generator_stage
from splurge_unittest_to_pytest.stages.collector import CollectorOutput, ClassInfo

DOMAINS = ["generator", "stages"]


def test_generator_creates_fixture_for_simple_literal_setup() -> None:
    src = """class T:
    def setUp(self):
        self.x = 42
    def tearDown(self):
        del self.x
"""
    module = cst.parse_module(src)
    class_node = next(n for n in module.body if isinstance(n, cst.ClassDef))
    ci = ClassInfo(node=class_node)
    # simulate collector behavior: record setup assignment and teardown stmt
    # find the assign node and teardown
    for stmt in class_node.body.body:
        if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "setUp":
            for s in stmt.body.body:
                if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], cst.Assign):
                    ci.setup_assignments.setdefault("x", []).append(s.body[0].value)
        if isinstance(stmt, cst.FunctionDef) and stmt.name.value == "tearDown":
            for s in stmt.body.body:
                ci.teardown_statements.append(s)
    collector = CollectorOutput(module=module, module_docstring_index=None, imports=(), classes={"T": ci})
    out = generator_stage({"collector_output": collector, "module": module})
    specs = out.get("fixture_specs") or {}
    nodes = out.get("fixture_nodes") or []
    assert "x" in specs
    assert any(isinstance(n, cst.FunctionDef) and n.name.value == "x" for n in nodes)
