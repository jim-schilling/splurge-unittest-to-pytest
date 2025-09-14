from splurge_unittest_to_pytest.main import convert_string


def test_assert_raises_conversion() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_foo(self) -> None:
        with self.assertRaises(ValueError):
            int('x')
"""
    out = convert_string(src).converted_code
    assert "with pytest.raises(ValueError):" in out


def test_assert_raises_regex_conversion() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_bar(self) -> None:
        with self.assertRaisesRegex(ValueError, 'invalid'):
            int('x')
"""
    out = convert_string(src).converted_code
    # Accept minor formatting differences (e.g., spacing around '='). Ensure
    # pytest.raises with ValueError and match pattern appears.
    assert "with pytest.raises(ValueError" in out and "match" in out and "invalid" in out


def test_assert_is_none_literal_skip() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_baz(self) -> None:
        self.assertIsNone(1)
"""
    out = convert_string(src).converted_code
    # For a literal int, the rewriter should skip conversion (leave as-is or not produce "is None")
    assert "is None" not in out
