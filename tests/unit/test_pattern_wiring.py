import libcst as cst
from splurge_unittest_to_pytest.main import PatternConfigurator
from splurge_unittest_to_pytest.stages.fixtures_stage import fixtures_stage


def test_pattern_configurator_causes_setup_removal():
    # Build a tiny module with a unittest.TestCase-derived class and a custom
    # setup method name 'my_setup' which we'll add to the PatternConfigurator.
    src = """
class TestX(unittest.TestCase):
    def my_setup(self):
        self.x = 1

    def test_foo(self):
        assert self.x == 1
"""
    module = cst.parse_module(src)

    # Build a collector-like minimal structure expected by fixtures_stage.
    # The fixtures_stage consults collector_output.classes for class info.
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

    # Ensure the resulting module does not contain a method named my_setup
    found = any(
        isinstance(stmt, cst.ClassDef)
        and any(isinstance(m, cst.FunctionDef) and m.name.value == "my_setup" for m in stmt.body.body)
        for stmt in new_mod.body
    )
    assert not found
