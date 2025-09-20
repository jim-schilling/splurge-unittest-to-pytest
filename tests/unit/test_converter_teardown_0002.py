import libcst as cst

from splurge_unittest_to_pytest.converter import teardown_helpers


def make_stmt(expr: str) -> cst.BaseStatement:
    return cst.parse_statement(expr)


def test_associate_cleanup_with_fixtures_appends_and_extends():
    mapping: dict[str, list[cst.BaseStatement]] = {}
    fixtures = ["one", "two"]
    cleanup = [make_stmt("x = 1"), make_stmt("del x")]
    teardown_helpers.associate_cleanup_with_fixtures(mapping, fixtures, cleanup)
    assert "one" in mapping and "two" in mapping
    assert len(mapping["one"]) == 2
    teardown_helpers.associate_cleanup_with_fixtures(mapping, ["two", "three"], [make_stmt("y=2")])
    assert len(mapping["two"]) == 3
    assert "three" in mapping
