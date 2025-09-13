import textwrap
import splurge_unittest_to_pytest.main as main


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
    res = main.convert_string(src, engine="pipeline", compat=True)
    out = res.converted_code
    # the autouse fixture should accept 'x' as a parameter (in its signature)
    # the autouse fixture should use request.getfixturevalue('x') to retrieve
    # the fixture deterministically and attach it onto the instance
    assert "getfixturevalue('x')" in out or 'getfixturevalue("x")' in out
    assert (
        "setattr(inst, 'x', request.getfixturevalue('x')" in out
        or "setattr(inst, 'x', request.getfixturevalue('x'))" in out
    )
