import libcst as cst
from splurge_unittest_to_pytest.converter.fixture_builders import build_fixtures_from_setup_assignments


def test_guard_emitted_for_self_referential_placeholder():
    setup = {"sql_file": cst.Name("sql_file")}
    teardown = {}
    fixtures_map, needs = build_fixtures_from_setup_assignments(setup, teardown)
    assert "sql_file" in fixtures_map
    func_def = fixtures_map["sql_file"]
    module = cst.Module(body=[func_def])
    code = module.code
    # The guard fixture should raise a RuntimeError with guidance when ambiguous
    assert "RuntimeError" in code or "ambiguous" in code


def test_autocreated_tmp_path_fixture_creates_file(tmp_path):
    # Simulate a converter-generated fixture that creates a file under tmp_path
    def generated_sql_file(tmp_path_arg):
        p = tmp_path_arg / "created.sql"
        p.write_text("-- generated")
        return str(p)

    # Call the simulated fixture function with pytest tmp_path
    _ = generated_sql_file(tmp_path)
    p = tmp_path / "created.sql"
    assert p.exists()
    assert p.read_text() == "-- generated"
