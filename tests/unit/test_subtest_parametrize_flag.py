import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCSTTransformer,
)


def test_parametrize_not_enabled_by_default():
    code = textwrap.dedent("""
    class MyTests(unittest.TestCase):
        def test_things(self):
            for i in [1,2,3]:
                with self.subTest(i):
                    assert check(i)
    """)
    out = UnittestToPytestCSTTransformer().transform_code(code)
    # Without flag, we expect no @pytest.mark.parametrize decorator (conservative default)
    assert "parametrize" not in out


def test_parametrize_enabled_converts_for_subtest():
    code = textwrap.dedent("""
    class MyTests(unittest.TestCase):
        def test_things(self):
            for i in [1,2,3]:
                with self.subTest(i):
                    assert check(i)
    """)
    out = UnittestToPytestCSTTransformer(parametrize=True).transform_code(code)
    # When enabled, parametrize should be added conservatively
    assert "@pytest.mark.parametrize" in out
    assert "def test_things" in out
