import libcst as cst

from splurge_unittest_to_pytest.main import PatternConfigurator
from splurge_unittest_to_pytest.stages.fixtures_stage import fixtures_stage


def test_pattern_configurator_causes_setup_removal():
    src = "\nclass TestX(unittest.TestCase):\n    def my_setup(self):\n        self.x = 1\n\n    def test_foo(self):\n        assert self.x == 1\n"
    module = cst.parse_module(src)

    class DummyClassInfo:
        def __init__(self, node):
            self.node = node
            self.setup_assignments = {"x": [cst.parse_expression("1")]}
            self.test_methods = []

    collector_output = type("C", (), {"classes": {"TestX": DummyClassInfo(module.body[0])}})()
    pc = PatternConfigurator()
    pc.add_setup_pattern("my_setup")
    ctx = {"module": module, "collector_output": collector_output, "pattern_config": pc}
    out = fixtures_stage(ctx)
    new_mod = out.get("module")
    found = any(
        (
            isinstance(stmt, cst.ClassDef)
            and any((isinstance(m, cst.FunctionDef) and m.name.value == "my_setup" for m in stmt.body.body))
            for stmt in new_mod.body
        )
    )
    assert not found
