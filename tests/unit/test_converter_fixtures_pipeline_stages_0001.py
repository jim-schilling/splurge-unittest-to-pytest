import libcst as cst
from libcst import parse_module
from splurge_unittest_to_pytest.stages.pipeline import run_pipeline
from splurge_unittest_to_pytest.converter.fixtures import parse_setup_assignments
from splurge_unittest_to_pytest.converter.method_patterns import is_setup_method, is_teardown_method, is_test_method


def test_pattern_matching_helpers():
    assert is_setup_method("setUp", {"setUp"})
    assert is_teardown_method("tearDown", {"tearDown"})
    assert is_test_method("test_something", {"test_"})


def test_remove_unittest_main_guard_with_pipeline():
    src = "if __name__ == '__main__':\n    import unittest\n    unittest.main()\n\na = 1\n"
    mod = parse_module(src)
    new = run_pipeline(mod, autocreate=False)
    assert "a = 1" in new.code
    assert "unittest.main" not in new.code


def test_assert_raises_converts_and_injects_pytest_import():
    src = "with self.assertRaises(ValueError):\n    raise ValueError()\n"
    mod = cst.parse_module(src)
    out = run_pipeline(mod, autocreate=False)
    assert "import pytest" in out.code


def test_parse_setup_assignments_empty_and_nonempty():
    src_empty = "class T:\n    def setUp(self):\n        pass\n"
    mod = parse_module(src_empty)
    func = next((n for n in getattr(mod.body[0].body, "body", []) if isinstance(n, cst.FunctionDef)), None)
    assigns = parse_setup_assignments(func)
    assert isinstance(assigns, dict)
    src = "class T:\n    def setUp(self):\n        self.x = 1\n"
    mod2 = parse_module(src)
    func2 = next((n for n in getattr(mod2.body[0].body, "body", []) if isinstance(n, cst.FunctionDef)), None)
    assigns2 = parse_setup_assignments(func2)
    assert "x" in assigns2
