import libcst as cst
from splurge_unittest_to_pytest.converter import raises


def make_arg(value_expr: cst.BaseExpression) -> cst.Arg:
    return cst.Arg(value=value_expr)


def test_make_pytest_raises_call_defaults_and_arg():
    # no args -> default Exception
    node = raises.make_pytest_raises_call([])
    assert isinstance(node, cst.Call)
    assert isinstance(node.func, cst.Attribute) and node.func.attr.value == "raises"

    # with arg
    a = make_arg(cst.Name("ValueError"))
    node2 = raises.make_pytest_raises_call([a])
    assert isinstance(node2, cst.Call)
    assert node2.args[0] is a


def test_make_pytest_raises_regex_call_and_withitem():
    exc = make_arg(cst.Name("KeyError"))
    regex = make_arg(cst.SimpleString('"pattern"'))
    node = raises.make_pytest_raises_regex_call([exc, regex])
    assert isinstance(node, cst.Call)
    # should include a keyword arg 'match'
    assert any(arg.keyword and getattr(arg.keyword, 'value', None) == 'match' for arg in node.args)

    # create with item from assertRaises
    with_item = raises.create_pytest_raises_withitem("assertRaises", [exc])
    assert isinstance(with_item, cst.WithItem)
    # for regex
    with_item2 = raises.create_pytest_raises_withitem("assertRaisesRegex", [exc, regex])
    assert isinstance(with_item2, cst.WithItem)
