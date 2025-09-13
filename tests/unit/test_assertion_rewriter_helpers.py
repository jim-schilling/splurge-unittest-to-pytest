from splurge_unittest_to_pytest.main import convert_string


def test_msg_keyword_removed_from_assert_equal() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_a(self) -> None:
        self.assertEqual(1, 2, msg='failure-reason')
"""
    out = convert_string(src).converted_code
    assert "failure-reason" not in out
    assert "assert 1 == 2" in out


def test_msg_positional_removed_from_assert_true() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_b(self) -> None:
        self.assertTrue(x == 1, 'why')
"""
    out = convert_string(src).converted_code
    # message should be removed; converted assertion should not contain the literal 'why'
    assert "why" not in out
    assert "assert x == 1" in out


def test_assert_almost_equal_keeps_numeric_third_positional_as_places() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_c(self) -> None:
        self.assertAlmostEqual(1.2345, 1.2344, 2)
"""
    out = convert_string(src).converted_code
    # when third positional is numeric it should be treated as 'places' -> round(..., 2) == 0
    assert "round(" in out and ", 2)" in out and "== 0" in out


def test_assert_almost_equal_non_numeric_third_positional_is_dropped_and_uses_approx() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_d(self) -> None:
        self.assertAlmostEqual(1.0, 1.1, 'note')
"""
    out = convert_string(src).converted_code
    # non-numeric third positional should be dropped (msg); default fallback uses pytest.approx
    assert "note" not in out
    assert "pytest.approx" in out


def test_assert_not_almost_equal_with_delta_kw() -> None:
    src = """
import unittest

class T(unittest.TestCase):
    def test_e(self) -> None:
        self.assertNotAlmostEqual(a, b, delta=0.1)
"""
    out = convert_string(src).converted_code
    # delta-based conversion should use abs(...) and a comparison with 0.1
    assert "abs(" in out and ">" in out and "0.1" in out
