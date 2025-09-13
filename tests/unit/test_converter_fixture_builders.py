import libcst as cst

from splurge_unittest_to_pytest.converter import fixture_builders


def test_build_fixtures_from_setup_assignments_creates_simple_and_cleanup():
    setup = {"a": cst.parse_expression("1"), "b": cst.parse_expression("2")}
    teardown = {"a": [cst.parse_statement("cleanup(self.a)")]}
    fixtures_map, needs_pytest = fixture_builders.build_fixtures_from_setup_assignments(setup, teardown)

    assert needs_pytest is True
    assert "a" in fixtures_map and "b" in fixtures_map
    # 'a' should be a cleanup fixture (yield) and 'b' a simple return fixture
    a_code = cst.Module(body=[fixtures_map["a"]]).code
    b_code = cst.Module(body=[fixtures_map["b"]]).code
    assert "yield _a_value" in a_code
    # b may be emitted as a direct return of the literal or as an assigned local then returned.
    assert ("return _b_value" in b_code) or ("return 2" in b_code)
