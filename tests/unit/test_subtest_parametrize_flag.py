import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def test_parametrize_enabled_by_default():
    code = textwrap.dedent("""
    class MyTests(unittest.TestCase):
        def test_things(self):
            for i in [1,2,3]:
                with self.subTest(i):
                    assert check(i)
    """)
    out = UnittestToPytestCstTransformer().transform_code(code)
    # Default behavior should parametrize simple subTest loops
    assert "@pytest.mark.parametrize" in out
    assert "for i in" not in out


def test_parametrize_disabled_retains_subtest_loop():
    code = textwrap.dedent("""
    class MyTests(unittest.TestCase):
        def test_things(self):
            for i in [1,2,3]:
                with self.subTest(i):
                    assert check(i)
    """)
    out = UnittestToPytestCstTransformer(parametrize=False).transform_code(code)
    # When disabled, no parametrize decorator should be added
    assert "@pytest.mark.parametrize" not in out
    assert "for i in" in out
