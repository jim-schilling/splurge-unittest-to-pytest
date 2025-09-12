from splurge_unittest_to_pytest.converter import utils


def test_parse_method_patterns_various():
    assert utils.parse_method_patterns(("setUp", "beforeAll")) == ["setUp", "beforeAll"]
    assert utils.parse_method_patterns(("  setUp  , beforeAll  ",)) == ["setUp", "beforeAll"]
    assert utils.parse_method_patterns(("a,a,b",)) == ["a", "b"]
    assert utils.parse_method_patterns(None) == []


def test_has_meaningful_changes_formatting_only():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 1\n"  # identical
    assert not utils.has_meaningful_changes(orig, conv)


def test_has_meaningful_changes_real_change():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 2\n"
    assert utils.has_meaningful_changes(orig, conv)


def test_normalize_method_name_edge_cases():
    assert utils.normalize_method_name("HTTPResponseCode") == "http_response_code"
    assert utils.normalize_method_name("setup_class") == "setup_class"
    assert utils.normalize_method_name("test123Case") == "test123_case"
