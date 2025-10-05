"""Unit tests for helpers.utility functions: sanitize_suffix and sanitize_extension."""

import pytest

from splurge_unittest_to_pytest.helpers import utility


@pytest.mark.parametrize(
    "input_s, expected",
    [
        ("dev", "_dev"),
        (".dev", "_dev"),
        ("..dev..", "_dev"),
        ("_dev-01", "_dev-01"),
        ("__..weird__--", "_weird"),
        ("..", ""),
        ("", ""),
        ("a!@#b", "_ab"),
        ("  space ", "_space"),
    ],
)
def test_sanitize_suffix_various(input_s, expected):
    assert utility.sanitize_suffix(input_s) == expected


@pytest.mark.parametrize(
    "input_e, expected",
    [
        ("py", ".py"),
        (".PY", ".py"),
        ("..py..", ".py"),
        (" .txt ", ".txt"),
        ("", None),
        (None, None),
        ("..", None),
        ("p@y", ".py"),
        ("1.2", ".12"),
    ],
)
def test_sanitize_extension_various(input_e, expected):
    assert utility.sanitize_extension(input_e) == expected
