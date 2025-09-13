import textwrap

from splurge_unittest_to_pytest.main import convert_string


def test_import_pytest_added_for_raises() -> None:
    src = textwrap.dedent("""
        import unittest

        class T(unittest.TestCase):
            def test_foo(self) -> None:
                with self.assertRaises(ValueError):
                    int('x')
    """)
    out = convert_string(src).converted_code
    assert "import pytest" in out


def test_import_pytest_not_added_when_unused() -> None:
    src = textwrap.dedent("""
        import unittest

        class T(unittest.TestCase):
            def test_bar(self) -> None:
                x = 1 + 1
                assert x == 2
    """)
    out = convert_string(src).converted_code
    assert "import pytest" not in out
