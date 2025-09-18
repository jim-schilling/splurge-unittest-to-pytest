from splurge_unittest_to_pytest.converter import helpers


def test_normalize_method_name_camel_to_snake():
    assert helpers.normalize_method_name("setUp") == "set_up"
    assert helpers.normalize_method_name("beforeAll") == "before_all"
    assert helpers.normalize_method_name("testSimpleCase") == "test_simple_case"


def test_parse_method_patterns_various_inputs():
    patterns = helpers.parse_method_patterns(("setUp", "beforeAll"))
    assert "setUp" in patterns and "beforeAll" in patterns
    patterns = helpers.parse_method_patterns(("  setUp  ,  beforeAll  ",))
    assert patterns == ["setUp", "beforeAll"]
    patterns = helpers.parse_method_patterns(("setUp,setUp,beforeAll",))
    assert patterns == ["setUp", "beforeAll"]
