from splurge_unittest_to_pytest.transformers.assert_with_rewrites import (
    _create_robust_regex,
    transform_caplog_alias_string_fallback,
)


def test_create_robust_regex_returns_input():
    pat = r"with\s+caplog"
    assert _create_robust_regex(pat) == pat


def test_transform_caplog_alias_string_fallback_replaces_output_and_exception():
    code = """
with self.assertLogs(logger) as lg:
    pass
alias.output[0]
alias.exception
"""

    out = transform_caplog_alias_string_fallback(code)
    assert "caplog.records" in out or "caplog.messages" in out or "value" in out
