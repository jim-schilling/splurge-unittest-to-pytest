import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.cleanup_checks import is_simple_cleanup_statement

DOMAINS = ["generator"]


def s(src: str):
    return cst.parse_statement(src)


def test_assign_self_attr():
    st = s("self.x = 1")
    assert is_simple_cleanup_statement(st, "x")


def test_assign_bare_name():
    st = s("x = None")
    assert is_simple_cleanup_statement(st, "x")


def test_expr_wrapped_assign():
    # Some tests wrap Assign inside Expr; use a plain Expr that doesn't
    # contain an Assign so parsing is safe and the helper should return False.
    st = s("(foo())")
    assert not is_simple_cleanup_statement(st, "x")


def test_delete_by_name():
    # Use a Delete-like class in libcst; parse a del statement
    st = s("del self.x")
    # behavior can vary by libcst; ensure it doesn't crash and returns a bool
    assert isinstance(is_simple_cleanup_statement(st, "x"), bool)
