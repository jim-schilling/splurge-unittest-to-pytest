import inspect

import libcst as cst

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def make_call_with_n_args(n: int) -> cst.Call:
    args = []
    if n >= 1:
        args.append(cst.Arg(value=cst.Name(value="a")))
    if n >= 2:
        args.append(cst.Arg(value=cst.Name(value="b")))
    if n >= 3:
        args.append(cst.Arg(value=cst.SimpleString(value='"r"')))
    return cst.Call(func=cst.Name(value="dummy"), args=args)


def test_transform_assert_functions_do_not_explode():
    # find all functions in module starting with transform_assert_
    funcs = [name for name, obj in inspect.getmembers(at, inspect.isfunction) if name.startswith("transform_assert_")]

    assert funcs, "No transform_assert_ functions found"

    for name in funcs:
        fn = getattr(at, name)
        # call with a 3-arg call to satisfy most signatures
        node = make_call_with_n_args(3)
        try:
            out = fn(node)
        except TypeError:
            # some functions may expect additional params; try calling with only node
            out = fn(node)
        # Ensure it returns a CST node or call didn't crash
        assert out is not None
