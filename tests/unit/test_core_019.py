import libcst as cst

from splurge_unittest_to_pytest.converter import params as conv_params

DOMAINS = ["core"]


def test_get_fixture_param_names_order():
    # construct minimal valid FunctionDef nodes via parsing a module
    a = cst.parse_module("def a():\n    pass\n").body[0]
    b = cst.parse_module("def b():\n    pass\n").body[0]
    fixtures = {"a": a, "b": b}
    names = conv_params.get_fixture_param_names(fixtures)
    assert set(names) == {"a", "b"}


def test_make_fixture_params_creates_params():
    p = conv_params.make_fixture_params(cst.Parameters(), ["fx", "fy"])
    assert isinstance(p, cst.Parameters)
    assert [param.name.value for param in p.params] == ["fx", "fy"]


def test_append_fixture_params_preserves_existing():
    existing = cst.Parameters(params=[cst.Param(name=cst.Name("x"))])
    p = conv_params.append_fixture_params(existing, ["fx"])
    assert [param.name.value for param in p.params] == ["x", "fx"]
