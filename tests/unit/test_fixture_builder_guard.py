import libcst as cst
from splurge_unittest_to_pytest.converter.fixture_builders import build_fixtures_from_setup_assignments


def test_self_referential_fixture_emits_guard():
    # simulate setUp assignment: self.sql_file = sql_file (placeholder)
    setup = {"sql_file": cst.Name("sql_file")}
    teardown = {}
    fixtures_map, needs = build_fixtures_from_setup_assignments(setup, teardown)
    assert "sql_file" in fixtures_map
    func_def = fixtures_map["sql_file"]
    # libcst.FunctionDef has no .code attribute; wrap in a Module to render
    module = cst.Module(body=[func_def])
    code = module.code
    # guard should raise RuntimeError with helpful message
    assert "RuntimeError" in code or "ambiguous" in code
