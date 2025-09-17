import textwrap
import splurge_unittest_to_pytest.main as main

DOMAINS = ["main"]


def test_autouse_fixture_accepts_fixture_params_and_attaches() -> None:
    src = textwrap.dedent("""
        import unittest

        class T(unittest.TestCase):
            def setUp(self) -> None:
                self.x = make_x()

            def test_use(self) -> None:
                self.assertEqual(self.x, 123)
    """)

    # run pipeline conversion
    res = main.convert_string(src)
    out = res.converted_code
    # Compatibility/autouse mode was removed. Expect strict pytest-style
    # conversion: a top-level fixture 'x' should be created and the
    # top-level test function should accept it as a parameter.
    assert "def x" in out or "def x(" in out
    assert "def test_use(x)" in out or "def test_use(x):" in out
