from splurge_unittest_to_pytest.converter.method_patterns import (
    normalize_method_name,
    is_setup_method,
    is_teardown_method,
    is_test_method,
)


def test_normalize_camel_to_snake():
    assert normalize_method_name("setUp") == "set_up"
    assert normalize_method_name("tearDown") == "tear_down"
    assert normalize_method_name("shouldDoThing") == "should_do_thing"


def test_is_setup_method_matches_common_names():
    patterns = {"setup", "before_each"}
    assert is_setup_method("setUp", patterns)
    assert is_setup_method("before_each", patterns)
    assert is_setup_method("setup_method", patterns)


def test_is_teardown_method_matches_common_names():
    patterns = {"teardown", "after_each"}
    assert is_teardown_method("tearDown", patterns)
    assert is_teardown_method("after_each", patterns)
    assert is_teardown_method("teardown_method", patterns)


def test_is_test_method_matches_prefixes():
    patterns = {"test_", "should_"}
    assert is_test_method("test_example", patterns)
    assert is_test_method("should_do_it", patterns)
    assert is_test_method("it_handles_case", {"it_"})
