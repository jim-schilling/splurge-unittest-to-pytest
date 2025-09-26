import libcst as cst
import pytest

from splurge_unittest_to_pytest.transformers import assert_transformer as at


def code_of(node) -> str:
    # Accept either an expression-like node (Call) or an Assert/Statement
    if isinstance(node, cst.Assert):
        mod = cst.Module(body=[cst.SimpleStatementLine(body=[node])])
    else:
        mod = cst.Module(body=[cst.SimpleStatementLine(body=[cst.Expr(value=node)])])
    return mod.code


@pytest.mark.parametrize(
    "call, expected",
    [
        (
            cst.Call(
                func=cst.Name("assertEqual"), args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("1"))]
            ),
            "==",
        ),
        (
            cst.Call(
                func=cst.Name("assertNotEqual"), args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("2"))]
            ),
            "!=",
        ),
        (cst.Call(func=cst.Name("assertTrue"), args=[cst.Arg(value=cst.Name("True"))]), "True"),
        (cst.Call(func=cst.Name("assertFalse"), args=[cst.Arg(value=cst.Name("False"))]), "not False"),
        (
            cst.Call(
                func=cst.Name("assertIs"), args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("1"))]
            ),
            "is",
        ),
        (
            cst.Call(
                func=cst.Name("assertIsNot"), args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Integer("2"))]
            ),
            "is not",
        ),
        (cst.Call(func=cst.Name("assertIsNone"), args=[cst.Arg(value=cst.Name("None"))]), "is None"),
        (cst.Call(func=cst.Name("assertIsNotNone"), args=[cst.Arg(value=cst.Name("x"))]), "is not None"),
        (
            cst.Call(
                func=cst.Name("assertIn"),
                args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.List([cst.Element(cst.Integer("1"))]))],
            ),
            "in [",
        ),
        (
            cst.Call(
                func=cst.Name("assertNotIn"),
                args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.List([cst.Element(cst.Integer("2"))]))],
            ),
            "not in",
        ),
        (
            cst.Call(
                func=cst.Name("assertIsInstance"),
                args=[cst.Arg(value=cst.SimpleString("'x'")), cst.Arg(value=cst.Name("str"))],
            ),
            "isinstance(",
        ),
        (
            cst.Call(
                func=cst.Name("assertNotIsInstance"),
                args=[cst.Arg(value=cst.Integer("1")), cst.Arg(value=cst.Name("str"))],
            ),
            "not isinstance(",
        ),
        (
            cst.Call(func=cst.Name("assertDictEqual"), args=[cst.Arg(value=cst.Dict([])), cst.Arg(value=cst.Dict([]))]),
            "==",
        ),
        (
            cst.Call(func=cst.Name("assertListEqual"), args=[cst.Arg(value=cst.List([])), cst.Arg(value=cst.List([]))]),
            "==",
        ),
        (
            cst.Call(
                func=cst.Name("assertSetEqual"),
                args=[
                    cst.Arg(value=cst.Call(func=cst.Name("set"), args=[])),
                    cst.Arg(value=cst.Call(func=cst.Name("set"), args=[])),
                ],
            ),
            "==",
        ),
        (
            cst.Call(
                func=cst.Name("assertTupleEqual"), args=[cst.Arg(value=cst.Tuple([])), cst.Arg(value=cst.Tuple([]))]
            ),
            "==",
        ),
        (
            cst.Call(
                func=cst.Name("assertCountEqual"),
                args=[
                    cst.Arg(value=cst.List([cst.Element(cst.Integer("1"))])),
                    cst.Arg(value=cst.List([cst.Element(cst.Integer("1"))])),
                ],
            ),
            "sorted(",
        ),
        (
            cst.Call(
                func=cst.Name("assertRaises"),
                args=[cst.Arg(value=cst.Name("ValueError")), cst.Arg(value=cst.Call(func=cst.Name("lambda"), args=[]))],
            ),
            "pytest.raises",
        ),
        (
            cst.Call(
                func=cst.Name("assertRegex"),
                args=[cst.Arg(value=cst.SimpleString("'abc'")), cst.Arg(value=cst.SimpleString("'a.'"))],
            ),
            "re.search",
        ),
        (
            cst.Call(
                func=cst.Name("assertNotRegex"),
                args=[cst.Arg(value=cst.SimpleString("'abc'")), cst.Arg(value=cst.SimpleString("'z+'"))],
            ),
            "re.search",
        ),
    ],
)
def test_direct_transforms(call: cst.Call, expected: str):
    # Map function name to transform function
    func_name = None
    if isinstance(call.func, cst.Name):
        func_name = call.func.value

    mapping = {
        "assertEqual": at.transform_assert_equal,
        "assertNotEqual": at.transform_assert_not_equal,
        "assertTrue": at.transform_assert_true,
        "assertFalse": at.transform_assert_false,
        "assertIs": at.transform_assert_is,
        "assertIsNot": at.transform_assert_is_not,
        "assertIsNone": at.transform_assert_is_none,
        "assertIsNotNone": at.transform_assert_is_not_none,
        "assertIn": at.transform_assert_in,
        "assertNotIn": at.transform_assert_not_in,
        "assertIsInstance": at.transform_assert_isinstance,
        "assertNotIsInstance": at.transform_assert_not_isinstance,
        "assertDictEqual": at.transform_assert_dict_equal,
        "assertListEqual": at.transform_assert_list_equal,
        "assertSetEqual": at.transform_assert_set_equal,
        "assertTupleEqual": at.transform_assert_tuple_equal,
        "assertCountEqual": at.transform_assert_count_equal,
        "assertRaises": at.transform_assert_raises,
        "assertRegex": at.transform_assert_regex,
        "assertNotRegex": at.transform_assert_not_regex,
    }

    assert func_name in mapping
    transformed = mapping[func_name](call)
    out = code_of(transformed)
    assert expected in out
