import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def test_two_pass_assert_statement_replacement():
    src = textwrap.dedent(
        """
        import unittest


        class MyTest(unittest.TestCase):
            def test_example(self):
                self.assertEqual(1, 2)

        """
    )

    t = UnittestToPytestCstTransformer()
    out = t.transform_code(src)

    # Final output should contain a plain pytest-style assert and not the original method call
    assert "assert 1 == 2" in out
    assert "assertEqual" not in out


def test_two_pass_assert_multiline_equal_replacement():
    src = textwrap.dedent(
        """
        import unittest


        class MyTest(unittest.TestCase):
            def test_multiline(self):
                self.assertMultiLineEqual('a', 'b')

        """
    )

    t = UnittestToPytestCstTransformer()
    out = t.transform_code(src)

    assert "assert 'a' == 'b'" in out or 'assert "a" == "b"' in out
    assert "assertMultiLineEqual" not in out
