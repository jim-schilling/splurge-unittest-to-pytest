from splurge_unittest_to_pytest.converter import helpers

DOMAINS = ["core"]


def test_parse_method_patterns_various():
    assert helpers.parse_method_patterns(("setUp", "beforeAll")) == ["setUp", "beforeAll"]
    assert helpers.parse_method_patterns(("  setUp  , beforeAll  ",)) == ["setUp", "beforeAll"]
    assert helpers.parse_method_patterns(("a,a,b",)) == ["a", "b"]
    assert helpers.parse_method_patterns(None) == []


def test_has_meaningful_changes_formatting_only():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 1\n"  # identical
    assert not helpers.has_meaningful_changes(orig, conv)


def test_has_meaningful_changes_real_change():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv)


def test_normalize_method_name_edge_cases():
    assert helpers.normalize_method_name("HTTPResponseCode") == "http_response_code"
    assert helpers.normalize_method_name("setup_class") == "setup_class"
    assert helpers.normalize_method_name("test123Case") == "test123_case"
