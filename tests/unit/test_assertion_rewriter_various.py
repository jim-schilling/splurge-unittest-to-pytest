import libcst as cst
import pytest

from splurge_unittest_to_pytest.stages.assertion_rewriter import assertion_rewriter_stage


def run(src: str):
    mod = cst.parse_module(src)
    return assertion_rewriter_stage({"module": mod})


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def test():\n    self.assertEqual(a, b)\n", "a == b"),
        ("def test():\n    self.assertNotEqual(x, y)\n", "x != y"),
        ("def test():\n    self.assertTrue(cond)\n", "cond"),
        ("def test():\n    self.assertFalse(cond2)\n", "not cond2"),
        ("def test():\n    self.assertListEqual(l1, l2)\n", "l1 == l2"),
        ("def test():\n    self.assertIs(a, b)\n", "a is b"),
        ("def test():\n    self.assertIsNot(x, y)\n", "x is not y"),
        ("def test():\n    self.assertIn(item, coll)\n", "item in coll"),
        ("def test():\n    self.assertNotIn(item2, coll2)\n", "item2 not in coll2"),
    ],
)
def test_various_simple_assertions(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code


def test_almost_equal_places_and_delta_and_default_approx():
    # places as third positional
    src1 = "def test():\n    self.assertAlmostEqual(a, b, 3)\n"
    out1 = run(src1)
    code1 = out1["module"].code
    assert "round(" in code1 or "pytest.approx" in code1

    # delta kw
    src2 = "def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n"
    out2 = run(src2)
    code2 = out2["module"].code
    assert "abs(" in code2 and "<= 0.1" in code2

    # default should use approx
    src3 = "def test():\n    self.assertAlmostEqual(a, b)\n"
    out3 = run(src3)
    code3 = out3["module"].code
    assert "pytest.approx" in code3


def test_regex_and_not_regex_and_re_import():
    src = "def test():\n    self.assertRegex(text, pattern)\n    self.assertNotRegex(text2, pattern2)\n"
    out = run(src)
    code = out["module"].code
    assert "re.search" in code
    assert "not re.search" in code or "not(" in code
    assert out.get("needs_re_import", False) is True


def test_raises_call_and_with_are_handled():
    src_call = "def test():\n    self.assertRaises(ValueError, func, arg)\n"
    out_call = run(src_call)
    code_call = out_call["module"].code
    # this form is skipped (converted to nothing) so original should remain
    assert "self.assertRaises" in code_call

    src_with = "def test():\n    with self.assertRaises(ValueError):\n        func()\n"
    out_with = run(src_with)
    code_with = out_with["module"].code
    assert "pytest.raises" in code_with
    assert out_with.get("needs_pytest_import", False) is True


@pytest.mark.parametrize(
    "src, expected_parts, needs_re",
    [
        ("def test():\n    self.assertRegex(text, pattern)\n", ["re.search"], True),
        ("def test():\n    assertRegex(text, pattern)\n", ["re.search"], True),
        ("def test():\n    self.assertRegexpMatches(text, pattern)\n", ["re.search"], True),
        ("def test():\n    self.assertNotRegex(text, pattern)\n", ["re.search", "not"], True),
        ("def test():\n    self.assertNotRegexpMatches(text, pattern)\n", ["re.search", "not"], True),
    ],
)
def test_regex_variants(src: str, expected_parts: list[str], needs_re: bool):
    out = run(src)
    code = out["module"].code
    for part in expected_parts:
        assert part in code
    assert out.get("needs_re_import", False) is needs_re


@pytest.mark.parametrize(
    "src, expected_checks",
    [
        # third positional numeric -> places -> round(...)
        ("def test():\n    self.assertAlmostEqual(a, b, 3)\n", [lambda s: "round(" in s or "pytest.approx" in s]),
        # delta kw -> abs(left - right) <= delta
        ("def test():\n    self.assertAlmostEqual(a, b, delta=0.1)\n", [lambda s: "abs(" in s and "<= 0.1" in s]),
        # explicit places kw
        ("def test():\n    self.assertAlmostEqual(a, b, places=2)\n", [lambda s: "round(" in s or "pytest.approx" in s]),
        # default -> pytest.approx
        ("def test():\n    self.assertAlmostEqual(a, b)\n", [lambda s: "pytest.approx" in s]),
    ],
)
def test_almost_equal_parametrized(src: str, expected_checks: list):
    out = run(src)
    code = out["module"].code
    for check in expected_checks:
        assert check(code)


@pytest.mark.parametrize(
    "src, expected_check",
    [
        ("def test():\n    self.assertNotAlmostEqual(a, b, delta=0.1)\n", lambda s: "abs(" in s and "> 0.1" in s),
        ("def test():\n    self.assertNotAlmostEqual(a, b, 2)\n", lambda s: "round(" in s or "pytest.approx" in s),
        ("def test():\n    self.assertNotAlmostEqual(a, b)\n", lambda s: "pytest.approx" in s),
    ],
)
def test_not_almost_equal_parametrized(src: str, expected_check):
    out = run(src)
    code = out["module"].code
    assert expected_check(code)


@pytest.mark.parametrize(
    "src, expected",
    [
        # trailing message positional should be dropped
        ("def test():\n    self.assertEqual(a, b, 'maybe')\n", "a == b"),
        # msg as keyword should be dropped
        ("def test():\n    self.assertEqual(a, b, msg='oops')\n", "a == b"),
        # assertIsNone with non-literal should produce 'is None'
        ("def test():\n    self.assertIsNone(x)\n", "x is None"),
        # assertIsNotNone with non-literal should produce 'is not None'
        ("def test():\n    self.assertIsNotNone(y)\n", "y is not None"),
    ],
)
def test_msg_and_is_none_variants(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code


@pytest.mark.parametrize(
    "src, expected_contains",
    [
        # almost equal with both delta kw and places kw
        ("def test():\n    self.assertAlmostEqual(a, b, delta=0.5, places=2)\n", ["abs(", "<= 0.5"]),
        # not almost equal with places kw (accept either '!= 0' or 'not round(...) == 0' form)
        ("def test():\n    self.assertNotAlmostEqual(a, b, places=1)\n", ["round(", ("!= 0", "not round")]),
        # almost equal with mixed positional+kw: third positional numeric kept as places
        ("def test():\n    self.assertAlmostEqual(a, b, 4, places=4)\n", ["round("]),
    ],
)
def test_almost_equal_extra_permutations(src: str, expected_contains: list[str]):
    out = run(src)
    code = out["module"].code
    for part in expected_contains:
        if isinstance(part, (list, tuple)):
            assert any(p in code for p in part)
        else:
            assert part in code


@pytest.mark.parametrize(
    "src, expected",
    [
        ("def test():\n    self.assertRegex(text, pattern, msg='x')\n", "re.search"),
        ("def test():\n    self.assertNotRegex(text, pattern, msg='x')\n", "re.search"),
    ],
)
def test_regex_with_msg_dropped(src: str, expected: str):
    out = run(src)
    code = out["module"].code
    assert expected in code
