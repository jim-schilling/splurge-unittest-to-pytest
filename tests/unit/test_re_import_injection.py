import textwrap

from splurge_unittest_to_pytest.main import convert_string


def test_import_re_added_for_assert_regex() -> None:
    src = textwrap.dedent("""
        import unittest

        class T(unittest.TestCase):
            def test_foo(self) -> None:
                self.assertRegex('abc', r'b.c')
    """)
    out = convert_string(src).converted_code
    assert "import re" in out


def test_import_re_not_added_when_unused() -> None:
    src = textwrap.dedent("""
        import unittest

        class T(unittest.TestCase):
            def test_bar(self) -> None:
                assert 1 == 1
    """)
    out = convert_string(src).converted_code
    assert "import re" not in out
