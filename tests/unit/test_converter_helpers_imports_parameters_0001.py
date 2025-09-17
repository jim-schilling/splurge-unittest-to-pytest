import libcst as cst
import textwrap
from splurge_unittest_to_pytest.converter import helpers, imports, params


def test_normalize_method_name_and_parse_patterns():
    assert helpers.normalize_method_name("setUp") == "set_up"
    assert helpers.normalize_method_name("tearDownNow") == "tear_down_now"
    patterns = helpers.parse_method_patterns(("test_, should_,", " it_ "))
    assert "test_" in patterns and "should_" in patterns and ("it_" in patterns)


def test_has_meaningful_changes_text_and_ast():
    orig = "def f():\n    return 1\n"
    conv = "def f():\n    return 1\n"
    assert helpers.has_meaningful_changes(orig, conv) is False
    conv2 = "def f():\n    return 2\n"
    assert helpers.has_meaningful_changes(orig, conv2) is True


def test_has_pytest_import_and_add(monkeypatch):
    src = textwrap.dedent('\n    """module doc"""\n\n    import os\n\n    def x():\n        pass\n    ')
    module = cst.parse_module(src)
    assert not imports.has_pytest_import(module)
    new_mod = imports.add_pytest_import(module)
    assert imports.has_pytest_import(new_mod)


def test_params_helpers():
    assert params.get_fixture_param_names({}) == []
    existing = cst.Parameters()
    p = params.make_fixture_params(["a", "b"])
    assert any((param.name.value == "a" for param in p.params))
    combined = params.append_fixture_params(existing, ["x"])
    assert any((param.name.value == "x" for param in combined.params))
