from splurge_unittest_to_pytest.converter import utils
from splurge_unittest_to_pytest import cli


def test_normalize_method_name_camel_to_snake():
    assert utils.normalize_method_name("setUp") == "set_up"
    assert utils.normalize_method_name("beforeAll") == "before_all"
    assert utils.normalize_method_name("testSimpleCase") == "test_simple_case"


def test_parse_method_patterns_various_inputs():
    # multiple flags
    patterns = cli._parse_method_patterns(("setUp", "beforeAll"))
    assert "setUp" in patterns and "beforeAll" in patterns

    # comma-separated with whitespace
    patterns = cli._parse_method_patterns(("  setUp  ,  beforeAll  ",))
    assert patterns == ["setUp", "beforeAll"]

    # duplicates removal preserves order
    patterns = cli._parse_method_patterns(("setUp,setUp,beforeAll",))
    assert patterns == ["setUp", "beforeAll"]
