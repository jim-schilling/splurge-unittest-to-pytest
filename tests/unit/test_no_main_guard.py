from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_transform_does_not_emit_main_guard():
    src = """
import unittest

class TestFoo(unittest.TestCase):
    def test_one(self):
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(src)
    assert "__name__" not in out or "__main__" not in out
