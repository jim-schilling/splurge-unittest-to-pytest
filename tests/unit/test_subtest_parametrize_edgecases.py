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


def test_nested_loop_not_parametrized():
    src = textwrap.dedent(
        """
        class TestNested(unittest.TestCase):
            def test_nested(self):
                for i in [1,2]:
                    for j in [3,4]:
                        with self.subTest(i=i, j=j):
                            self.assertTrue(True)
        """
    )
    out = _transform(src)
    # Should not parametrize nested loops with multi-arg subTest; keep loops and use subtests
    assert "@pytest.mark.parametrize" not in out
    assert "for i in" in out and "for j in" in out


def test_multiple_subtests_in_loop_not_parametrized():
    src = textwrap.dedent(
        """
        class TestMulti(unittest.TestCase):
            def test_multi(self):
                for x in [1,2]:
                    with self.subTest(x=x):
                        self.assertTrue(x)
                    with self.subTest(x=x):
                        self.assertFalse(not x)
        """
    )
    out = _transform(src)
    # Multiple subTest blocks for same loop should not be auto-parametrized conservatively
    assert "@pytest.mark.parametrize" not in out


def test_combined_keyword_and_positional_unsupported():
    src = textwrap.dedent(
        """
        class TestBad(unittest.TestCase):
            def test_bad(self):
                for a in [1,2]:
                    with self.subTest(a, a=a):
                        self.assertTrue(a)
        """
    )
    out = _transform(src)
    # Combined positional+keyword should remain unchanged (unsupported)
    assert "@pytest.mark.parametrize" not in out


def test_idempotent_when_already_parametrized():
    src = textwrap.dedent(
        """
        class TestAlready(unittest.TestCase):
            @pytest.mark.parametrize("n", [1,2])
            def test_already(self, n):
                for x in [1,2]:
                    with self.subTest(x=x):
                        self.assertTrue(x)
        """
    )
    out = _transform(src)
    # We should not add a second parametrize decorator or change existing marks
    assert out.count("@pytest.mark.parametrize") == 1
