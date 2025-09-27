def test_subtest_cst_conversion_adds_subtests_param_and_rewrites_with():
    import libcst as cst

    from splurge_unittest_to_pytest.transformers.unittest_transformer import (
        UnittestToPytestCSTTransformer as UnittestToPytestTransformer,
    )

    code = """
class MyTests(unittest.TestCase):
    def test_things(self):
        with self.subTest(i=1):
            assert do_one()
"""

    transformer = UnittestToPytestTransformer()
    out = transformer.transform_code(code)

    # After transform, the with should use subtests.test and function should accept subtests param
    assert "with subtests.test(i=1):" in out
    assert "def test_things(self, subtests)" in out or "def test_things(self, subtests):" in out
