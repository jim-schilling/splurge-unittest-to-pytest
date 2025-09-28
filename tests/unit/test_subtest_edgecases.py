import libcst as cst

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def _transform(code: str) -> str:
    tr = UnittestToPytestCstTransformer()
    return tr.transform_code(code)


def test_subtest_in_nested_blocks():
    code = """
class MyTests(unittest.TestCase):
    def test_nested(self):
        if cond:
            for i in range(2):
                with self.subTest(i=i):
                    assert check(i)
"""
    out = _transform(code)
    # ensure subtests.test appears and nested structure preserved
    assert "with subtests.test(i=i):" in out
    assert "for i in range(2):" in out


def test_multiple_statements_under_subtest_only_first_wrapped():
    # If multiple statements are intended under subTest, our transformer only
    # rewrites the With node body in-place; ensure the body stays intact.
    code = """
class MyTests(unittest.TestCase):
    def test_multi(self):
        with self.subTest(i=1):
            a = setup()
            assert do_one(a)
            teardown(a)
"""
    out = _transform(code)
    # We expect subtests.test present and the multiple statements preserved
    assert "with subtests.test(i=1):" in out
    assert "a = setup()" in out
    assert "teardown(a)" in out


def test_subtest_positional_and_keyword_args():
    code = """
class MyTests(unittest.TestCase):
    def test_args(self):
        with self.subTest(1, name="one"):
            assert do_one(1)
"""
    out = _transform(code)
    # positional and keyword args should be preserved in the new call
    assert 'with subtests.test(1, name="one"):' in out or "with subtests.test(1, name='one'):" in out


def test_class_level_subtest_usage():
    code = """
class MyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def test_classlevel(self):
        with self.subTest():
            assert True
"""
    out = _transform(code)
    # ensure we still rewrite the subTest to subtests.test
    assert "with subtests.test()" in out
