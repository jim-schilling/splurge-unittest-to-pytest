import libcst as cst

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    transform_caplog_alias_string_fallback,
    wrap_assert_logs_in_block,
)


def _module_from_statements(src: str) -> cst.Module:
    return cst.parse_module(src)


def test_wrap_assert_logs_bare_calls_turn_into_with():
    src = """
def test_fn(self):
    self.assertLogs('my.logger', level='INFO')
    do_something()
"""
    mod = _module_from_statements(src)
    # extract function body statements
    func = mod.body[0]
    assert isinstance(func, cst.FunctionDef)
    stmts = list(func.body.body)

    out = wrap_assert_logs_in_block(stmts)
    # Expect a single With node at start
    assert any(isinstance(s, cst.With) for s in out)
    code = cst.Module(body=out).code
    assert "caplog.at_level" in code


def test_alias_rewrite_len_and_in_membership():
    src = """
with self.assertLogs('my.logger', level='INFO') as log:
    assert len(log.output) == 2
    assert 'started' in log.output[0]
"""

    out = transform_caplog_alias_string_fallback(src)
    assert "log.output" not in out
    assert "caplog.records" in out
    assert ".getMessage()" in out
