import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_with_rewrites as aw


def test_get_caplog_level_args_positional():
    call = cst.Call(
        func=cst.Name(value="assertLogs"),
        args=[
            cst.Arg(value=cst.SimpleString(value='"logger"')),
            cst.Arg(value=cst.Attribute(value=cst.Name(value="logging"), attr=cst.Name(value="INFO"))),
        ],
    )
    args = aw.get_caplog_level_args(call)
    assert len(args) == 1


def test_get_caplog_level_args_keyword():
    call = cst.Call(
        func=cst.Name(value="assertLogs"),
        args=[
            cst.Arg(
                keyword=cst.Name(value="level"),
                value=cst.Attribute(value=cst.Name(value="logging"), attr=cst.Name(value="DEBUG")),
            )
        ],
    )
    args = aw.get_caplog_level_args(call)
    assert len(args) == 1


def test_build_caplog_call_defaults_to_info():
    call = cst.Call(func=cst.Name(value="assertLogs"), args=[])
    built = aw.build_caplog_call(call)
    assert isinstance(built.func, cst.Attribute)
    assert built.func.attr.value == "at_level"
