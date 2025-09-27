from splurge_unittest_to_pytest.transformers.assert_transformer import transform_assertions_string_based


def test_transform_assertions_basic_equal_and_true():
    src = """
class ExampleTest(unittest.TestCase):
    def test_something(self):
        self.assertEqual(a, b)
        self.assertTrue(x)
"""

    out = transform_assertions_string_based(src)

    assert "assert a == b" in out
    assert "assert x" in out


def test_transform_assertions_normalize_test_name_and_raises():
    src = """
class ExampleTest(unittest.TestCase):
    def testSomething(self):
        with self.assertRaises(ValueError):
            do_it()
"""

    out = transform_assertions_string_based(src)

    # name should be normalized (underscore inserted; capitalization is preserved)
    assert "def test_Something(self)" in out
    # assertRaises should be rewritten to pytest.raises (allow for formatting/newline)
    assert "pytest.raises(ValueError" in out
