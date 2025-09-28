from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_transform_assertions_basic_equal_and_true():
    src = """
class ExampleTest(unittest.TestCase):
    def test_something(self):
        self.assertEqual(a, b)
        self.assertTrue(x)
"""

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(src)

    assert "assert a == b" in out
    assert "assert x" in out


def test_transform_assertions_normalize_test_name_and_raises():
    src = """
class ExampleTest(unittest.TestCase):
    def testSomething(self):
        with self.assertRaises(ValueError):
            do_it()
"""

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(src)

    # name should be normalized (underscore inserted; capitalization is preserved)
    assert "def test_Something(self)" in out
    # assertRaises should be rewritten to pytest.raises (allow for formatting/newline)
    assert "pytest.raises(ValueError" in out
