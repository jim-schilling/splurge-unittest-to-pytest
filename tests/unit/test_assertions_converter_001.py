from splurge_unittest_to_pytest.converter.assertion_dispatch import convert_assertion
import libcst as cst

DOMAINS = ["assertions", "converter"]


def test_convert_equal():
    node = convert_assertion("assertEqual", [cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("2"))])
    assert isinstance(node, cst.Assert)


def test_convert_unknown():
    node = convert_assertion("assertDoesNotExist", [])
    assert node is None
