import textwrap

import libcst as cst

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCSTTransformer,
)


def _transform(src: str, parametrize: bool = True) -> str:
    mod = cst.parse_module(src)
    transformer = UnittestToPytestCSTTransformer(parametrize=parametrize)
    new = mod.visit(transformer)
    return new.code


def test_parametrize_with_literal_list():
    src = textwrap.dedent(
        """
        class TestSomething(unittest.TestCase):
            def test_values(self):
                for i in [1, 2, 3]:
                    with self.subTest(i=i):
                        self.assertEqual(i % 2, 1)
        """
    )

    out = _transform(src)
    # Expect @pytest.mark.parametrize and function body without the for loop
    assert '@pytest.mark.parametrize("i", [1, 2, 3])' in out
    assert "for i in" not in out


def test_parametrize_with_tuple_and_multiple_statements():
    src = textwrap.dedent(
        """
        class TestMultiple(unittest.TestCase):
            def test_multi(self):
                for x in ("a", "b"):
                    with self.subTest(x=x):
                        val = x.upper()
                        self.assertIn(val, ["A", "B"])
        """
    )

    out = _transform(src)
    assert "@pytest.mark.parametrize(\"x\", ['a', 'b'])" in out or '@pytest.mark.parametrize("x", ["a", "b"])' in out
    assert "for x in" not in out
    assert "val = x.upper()" in out
