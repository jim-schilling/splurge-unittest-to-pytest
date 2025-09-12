import libcst as cst

from splurge_unittest_to_pytest.converter.class_checks import is_unittest_testcase_base


def _make_attr(base_src: str) -> cst.Arg:
    module = cst.parse_module(base_src)
    # Expecting a single expression like: unittest.TestCase or TestCase
    # module.body[0] is a SimpleStatementLine; extract the inner expression safely
    # mypy: stmt may be a BaseStatement; use cst.Module.code_for_node to render then parse again
    expr = module.body[0].body[0].value
    return cst.Arg(value=expr)


def test_unittest_testcase_attribute():
    arg = _make_attr("unittest.TestCase")
    assert is_unittest_testcase_base(arg)


def test_bare_testcase_name():
    arg = _make_attr("TestCase")
    assert is_unittest_testcase_base(arg)


def test_non_testcase_returns_false():
    arg = _make_attr("object")
    assert not is_unittest_testcase_base(arg)
