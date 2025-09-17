
from splurge_unittest_to_pytest import main


def test_convert_string_parser_error_returns_errors():
    invalid = "def f(:\n    pass"
    res = main.convert_string(invalid)
    assert not res.has_changes
    assert res.errors


def test_pattern_configurator_add_and_detection():
    pc = main.PatternConfigurator()
    pc.add_setup_pattern("my_setup")
    assert "my_setup" in pc.setup_patterns
    # test detection helpers
    assert pc._is_setup_method("setUp")
    assert not pc._is_teardown_method("not_a_teardown")
    assert pc._is_test_method("test_example")
