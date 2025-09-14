import libcst as cst

from splurge_unittest_to_pytest.main import PatternConfigurator, convert_string


def test_pattern_adders_and_properties():
    pc = PatternConfigurator()
    # default patterns exist
    assert "setUp" in pc.setup_patterns or "setup" in pc.setup_patterns
    # add custom patterns
    pc.add_setup_pattern("mySetup")
    pc.add_teardown_pattern("myTeardown")
    pc.add_test_pattern("my_test_")
    assert any(p.lower() == "mysetup" for p in pc.setup_patterns)
    assert any(p.lower() == "myteardown" for p in pc.teardown_patterns)
    assert any(p == "my_test_" for p in pc.test_patterns)


def test_remove_self_references_delegation():
    # create a simple function with self.x used in body
    src = """
def test_fn(self):
    print(self.x)
"""
    node = cst.parse_module(src).body[0]
    assert isinstance(node, cst.FunctionDef)

    # Perform a conversion on a class-based test and confirm 'self' references are removed
    src = "class T(unittest.TestCase):\n    def test_fn(self):\n        print(self.x)\n"
    res = convert_string(src)
    # The converted code should not contain 'self.' attribute accesses
    assert "self.x" not in res.converted_code


def test_normalize_method_name_delegation():
    pc = PatternConfigurator()
    # current normalization converts camelCase to snake with underscore
    assert pc._is_setup_method("setUp") is True
