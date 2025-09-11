import libcst as cst

from splurge_unittest_to_pytest.converter.teardown_helpers import (
    associate_cleanup_with_fixtures,
)


def make_stmt(expr_src: str) -> cst.BaseStatement:
    mod = cst.parse_module(expr_src)
    # Return the first statement for simplicity
    return mod.body[0]


def test_associate_cleanup_with_fixtures_basic():
    teardown_cleanup: dict[str, list[cst.BaseStatement]] = {}
    fixtures = ["fix_a", "fix_b"]
    cleanup_stmts = [make_stmt("self.resource.close()"), make_stmt("del self.value")]

    associate_cleanup_with_fixtures(teardown_cleanup, fixtures, cleanup_stmts)

    # Each fixture should have a copy of the cleanup statements
    assert set(teardown_cleanup.keys()) == set(fixtures)
    for v in teardown_cleanup.values():
        assert len(v) == 2
        # Ensure items are libcst statements
        assert all(isinstance(s, cst.BaseStatement) for s in v)
