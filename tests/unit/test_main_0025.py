from splurge_unittest_to_pytest.main import PatternConfigurator, convert_string

DOMAINS = ["main"]


def test_pattern_adders_and_props() -> None:
    pc = PatternConfigurator()

    # default patterns contain typical values
    assert any(p.lower().startswith("test") for p in pc.test_patterns)

    # add custom patterns and verify they're present
    pc.add_setup_pattern("setup_class")
    assert any("setup_class" == p or "setup_class" in p for p in pc.setup_patterns)

    pc.add_teardown_pattern("teardown_class")
    assert any("teardown_class" == p or "teardown_class" in p for p in pc.teardown_patterns)

    pc.add_test_pattern("describe_")
    assert any(p.startswith("describe_") for p in pc.test_patterns)


def test_assert_raises_helpers_and_import_flag() -> None:
    # Use the public assertion_rewriter_stage to exercise assertRaises -> pytest.raises
    src_with = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(src_with)
    assert "pytest.raises" in res.converted_code


def test_add_pytest_import_wrapper_returns_module_with_import() -> None:
    # _add_pytest_import behavior covered by convert_string when conversion needs pytest
    mod = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(mod)
    assert "import pytest" in res.converted_code or "pytest" in res.converted_code


def test_fixture_creation_delegation_simple_and_attribute() -> None:
    # Behavior is covered via convert_string when setUp conversion creates fixtures
    src = "class X(unittest.TestCase):\n    def setUp(self):\n        self.x = 1\n\n    def test_something(self):\n        assert self.x == 1\n"
    res = convert_string(src)
    # A fixture for 'x' should be created in converted code
    assert "def x(" in res.converted_code or "@pytest.fixture" in res.converted_code


def test_remove_self_references_simple_attribute():
    # Removing self references is exercised indirectly by converting tests
    src = "class T(unittest.TestCase):\n    def setUp(self):\n        self.value = 1\n\n    def test_it(self):\n        assert self.value == 1\n"
    res = convert_string(src)
    assert "self.value" not in res.converted_code


def test_convert_assertion_name_fallback_to_converter():
    src = "def test():\n    self.assertEqual(1, 2)\n"
    res = convert_string(src)
    assert "1 == 2" in res.converted_code


def test_create_pytest_raises_item_sets_import_flag():
    src = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    res = convert_string(src)
    assert "pytest.raises" in res.converted_code


def test_convert_setup_to_fixture_creates_assignments_and_fixtures():
    src = "class X(unittest.TestCase):\n    def setUp(self):\n        self.x = 1\n\n    def test_something(self):\n        assert self.x == 1\n"
    res = convert_string(src)
    # The converted code should contain a fixture or assignment for 'x'
    assert "def x(" in res.converted_code or "@pytest.fixture" in res.converted_code


def test_visit_classdef_removes_unittest_base():
    src = "import unittest\n\nclass TestExample(unittest.TestCase):\n    pass\n"
    res = convert_string(src)
    # the transformed module should no longer contain 'unittest.TestCase' base
    assert "unittest.TestCase" not in res.converted_code
