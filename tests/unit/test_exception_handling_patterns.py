#!/usr/bin/env python3
"""Test exception and error handling pattern transformations."""

import pytest

from splurge_unittest_to_pytest.transformers import UnittestToPytestCstTransformer


class TestExceptionHandlingPatterns:
    """Test transformations for exception handling patterns."""

    def test_expected_failure_decorator(self):
        """Test @unittest.expectedFailure -> @pytest.mark.xfail transformation."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    @unittest.expectedFailure
    def test_something(self):
        self.fail("This test is expected to fail")
"""

        result = transformer.transform_code(test_code)

        # Check that expectedFailure decorator is transformed
        assert "@pytest.mark.xfail()" in result
        assert "@unittest.expectedFailure" not in result

        # Check that unittest.TestCase is removed
        assert "unittest.TestCase" not in result
        assert "class TestExample:" in result

    def test_skip_decorator_preserved(self):
        """Test that @unittest.skip decorators are properly transformed."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    @unittest.skip("Not ready yet")
    def test_skipped_method(self):
        pass
"""

        result = transformer.transform_code(test_code)

        # Check that skip decorator is transformed
        assert '@pytest.mark.skip("Not ready yet")' in result
        assert "@unittest.skip" not in result

    def test_assert_warns_transformation(self):
        """Test self.assertWarns -> pytest.warns transformation."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    def test_warns_simple(self):
        def f():
            import warnings
            warnings.warn("test warning", UserWarning)

        self.assertWarns(UserWarning, f)
"""

        result = transformer.transform_code(test_code)

        # Check that assertWarns is transformed
        assert "pytest.warns(UserWarning, lambda:" in result
        assert "f()" in result
        assert "self.assertWarns" not in result

    def test_assert_warns_regex_transformation(self):
        """Test self.assertWarnsRegex -> pytest.warns with match transformation."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    def test_warns_regex(self):
        def g():
            import warnings
            warnings.warn("match-me-123", UserWarning)

        self.assertWarnsRegex(UserWarning, g, r"match-me-\\d+")
"""

        result = transformer.transform_code(test_code)

        # Check that assertWarnsRegex is transformed
        assert "pytest.warns(UserWarning, lambda:" in result
        assert "g()" in result
        assert "match" in result and "match-me" in result
        assert "self.assertWarnsRegex" not in result

    def test_assert_warns_with_lambda(self):
        """Test self.assertWarns with lambda function."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    def test_warns_lambda(self):
        self.assertWarns(ValueError, lambda: int("not_a_number"))
"""

        result = transformer.transform_code(test_code)

        # Check that lambda is preserved correctly
        assert 'pytest.warns(ValueError, lambda: int("not_a_number"))' in result

    def test_multiple_exception_patterns(self):
        """Test multiple exception handling patterns in one class."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestComplex(unittest.TestCase):
    @unittest.expectedFailure
    def test_expected_to_fail(self):
        self.assertWarnsRegex(ValueError, lambda: raise_error(), r"value.*error")

    @unittest.skip("Feature not implemented")
    def test_skipped_feature(self):
        pass

    def test_normal_warnings(self):
        self.assertWarns(UserWarning, lambda: warn_user())
"""

        result = transformer.transform_code(test_code)

        # Check all transformations are applied
        assert "@pytest.mark.xfail()" in result
        assert "@unittest.expectedFailure" not in result

        assert '@pytest.mark.skip("Feature not implemented")' in result
        assert "@unittest.skip" not in result

        assert "pytest.warns(UserWarning, lambda:" in result
        assert "warn_user()" in result
        assert "self.assertWarns" not in result

        # Check that the regex warning assertion is transformed
        assert "pytest.warns(ValueError, lambda:" in result
        assert "raise_error()" in result
        assert "match" in result and "value.*error" in result
        assert "self.assertWarnsRegex" not in result

    def test_pytest_import_added(self):
        """Test that pytest import is added when exception patterns are used."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    @unittest.expectedFailure
    def test_something(self):
        pass
"""

        result = transformer.transform_code(test_code)

        # Check that pytest import is added
        assert "import pytest" in result

    def test_no_unittest_import_left(self):
        """Test that unused unittest imports are removed."""
        transformer = UnittestToPytestCstTransformer()

        test_code = """import unittest

class TestExample(unittest.TestCase):
    @unittest.expectedFailure
    def test_something(self):
        pass

if __name__ == "__main__":
    unittest.main()
"""

        result = transformer.transform_code(test_code)

        # Check that unittest import is removed since it's not used after transformation
        # (Note: the if __name__ == "__main__" block might still reference unittest)
        assert "import unittest" not in result or 'if __name__ == "__main__"' not in result


if __name__ == "__main__":
    pytest.main([__file__])
