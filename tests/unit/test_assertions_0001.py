from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.converter import assertions


def build_call(name: str, arg_expr: cst.BaseExpression) -> cst.Call:
    return cst.Call(func=cst.Name(name), args=[cst.Arg(value=arg_expr)])


def test_assert_equal_mapping_happy_path() -> None:
    # Simulate assertEqual(a, b) -> ASSERTIONS_MAP should provide handler
    handler = assertions.ASSERTIONS_MAP.get("assertEqual")
    assert handler is not None


def test_assert_is_none_edgecases() -> None:
    # Ensure mapping exists for assertIsNone and handles literal None
    handler = assertions.ASSERTIONS_MAP.get("assertIsNone")
    assert handler is not None

    # The handler is expected to accept a libcst.Call or similar; at minimum ensure callable
    _ = build_call("assertIsNone", cst.Name("None"))
    assert callable(handler)


def test_assert_true_false_mapping() -> None:
    # Check both assertTrue and assertFalse mappings exist
    assert "assertTrue" in assertions.ASSERTIONS_MAP
    assert "assertFalse" in assertions.ASSERTIONS_MAP
