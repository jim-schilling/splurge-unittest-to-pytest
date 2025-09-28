import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_skip_decorator_rewrite():
    code = textwrap.dedent("""
        import unittest

        @unittest.skip("reason")
        class TestX(unittest.TestCase):
            def test_a(self):
                self.assertTrue(True)
    """)

    out = UnittestToPytestCstTransformer().transform_code(code)
    # Transformer should at least add pytest import and preserve the class
    assert "import pytest" in out
    assert "class TestX" in out
