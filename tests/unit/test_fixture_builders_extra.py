import libcst as cst

from splurge_unittest_to_pytest.converter.fixture_builders import build_fixtures_from_setup_assignments


def test_build_fixtures_with_and_without_cleanup():
    setup = {'x': cst.parse_expression('1'), 'y': cst.parse_expression("'v'")}
    teardown = {'x': [cst.parse_statement('del self.x')]}
    fixtures, needs = build_fixtures_from_setup_assignments(setup, teardown)
    assert isinstance(fixtures, dict)
    assert 'x' in fixtures and 'y' in fixtures
    assert needs is True
    # Each fixture should be a FunctionDef
    for f in fixtures.values():
        assert isinstance(f, cst.FunctionDef)
