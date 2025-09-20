import libcst as cst

from splurge_unittest_to_pytest.stages import assertion_rewriter, fixture_injector, import_injector
from splurge_unittest_to_pytest.stages.collector import Collector, CollectorOutput
from splurge_unittest_to_pytest.stages.generator import generator_stage


def test_references_attribute_detects_in_if_call_and_subscript():
    module = cst.parse_module("x = 0\n")
    cls_info = type("CI", (), {})()
    cls_info.setup_assignments = {"v": [cst.Integer("1")]}
    if_stmt = cst.parse_statement("if self.v:\n    pass")
    call_stmt = cst.parse_statement("f(self.v)")
    sub_stmt = cst.parse_statement("a[self.v]")
    cls_info.teardown_statements = [if_stmt, call_stmt, sub_stmt]
    out = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=True
    )
    res = generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    assert "v" in specs
    assert specs["v"].cleanup_statements, "teardown statements referencing attribute should be detected"


def test_delete_detection_and_rendered_fallback():
    module = cst.parse_module("x = 0\n")
    cls_info = type("CI", (), {})()
    cls_info.setup_assignments = {"y": [cst.Integer("2")]}
    del_stmt = cst.parse_statement("del self.y")
    cls_info.teardown_statements = [del_stmt]
    out = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=True
    )
    res = generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    assert "y" in specs
    assert specs["y"].cleanup_statements, "del statements should be considered cleanup"


def test_non_literal_return_binds_to_local_and_returns_local():
    module = cst.parse_module("x = 0\n")
    cls_info = type("CI", (), {})()
    cls_info.setup_assignments = {"a": [cst.parse_expression("make()")]}
    cls_info.teardown_statements = []
    out = CollectorOutput(
        module=module, module_docstring_index=None, imports=[], classes={"C": cls_info}, has_unittest_usage=False
    )
    res = generator_stage({"collector_output": out, "module": module})
    specs = res.get("fixture_specs")
    nodes = res.get("fixture_nodes")
    assert "a" in specs
    rendered = "\n\n".join((cst.Module(body=[n]).code for n in nodes or []))
    assert "_a_value" in rendered or "return make()" in rendered or "yield make()" in rendered


def test_pipeline_integration_basic_flow():
    src = "\nclass C:\n    def setUp(self):\n        self.x = 1\n\n    def tearDown(self):\n        self.x = None\n\n    def test_it(self):\n        self.assertEqual(self.x, 1)\n"
    module = cst.parse_module(src)
    wrapper = cst.MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    gen_res = generator_stage({"collector_output": out, "module": module})
    fixture_nodes = gen_res.get("fixture_nodes") or []
    inj_res = fixture_injector.fixture_injector_stage(
        {"module": module, "fixture_nodes": fixture_nodes, "collector_output": out}
    )
    mod2 = inj_res.get("module")
    rewrite_res = assertion_rewriter.assertion_rewriter_stage({"module": mod2})
    mod3 = rewrite_res.get("module")
    import_res = import_injector.import_injector_stage(
        {"module": mod3, "needs_pytest_import": rewrite_res.get("needs_pytest_import", False)}
    )
    final = import_res.get("module")
    code = final.code
    assert "import pytest" in code
    assert "assert self.x == 1" in code
