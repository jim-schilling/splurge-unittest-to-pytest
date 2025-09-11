import libcst as cst

from splurge_unittest_to_pytest.converter.params import append_fixture_params


def test_append_fixture_params_preserves_existing():
    existing = cst.Parameters(params=[cst.Param(name=cst.Name("a"))])
    out = append_fixture_params(existing, ["f1", "f2"])
    names = [p.name.value for p in out.params]
    assert names == ["a", "f1", "f2"]
